import threading
from typing import List
from datetime import datetime, timezone, timedelta, time
from time import sleep

from helpers.config import SpeedrrConfig, ScheduleConfig
from helpers.log_loader import logger



class ScheduleModule:
    "A module that manages schedules."

    def __init__(self, config: SpeedrrConfig, module_configs: List[ScheduleConfig], update_event: threading.Event) -> None:
        self.reduction_value_dict: dict[ScheduleConfig, tuple[float, float]] = {}

        self._config = config
        self._module_configs = module_configs
        self._update_event = update_event
    
    
    def get_reduction_value(self) -> tuple[float, float]:
        "How much to reduce the speed by, in the config's units. Returns a tuple of `(upload, download)`."

        logger.info(f"<schedule> Upload reduction values = {'; '.join(f'{cfg.start}-{cfg.end}: {reduction[0]}' for cfg, reduction in self.reduction_value_dict.items())}")
        logger.info(f"<schedule> Download reduction values = {'; '.join(f'{cfg.start}-{cfg.end}: {reduction[1]}' for cfg, reduction in self.reduction_value_dict.items())}")
        
        return (
            sum([reduction[0] for reduction in self.reduction_value_dict.values()]),
            sum([reduction[1] for reduction in self.reduction_value_dict.values()]),
        )
    

    def run(self) -> None:
        "Start the schedule threads."

        logger.debug("<schedule> Starting schedule module threads")
        for module_config in self._module_configs:
            thread = ScheduleThread(module_config, self)
            thread.daemon = True
            thread.start()



class ScheduleThread(threading.Thread):
    "A thread that manages a schedule."

    def __init__(self, config: ScheduleConfig, module: ScheduleModule) -> None:
        threading.Thread.__init__(self)
        
        self._config = config
        self._module = module

        self._start_hour, self._start_minute = map(int, self._config.start.split(':'))
        self._end_hour, self._end_minute = map(int, self._config.end.split(':'))

        self._days_as_int = []
        for day in self._config.days:
            if day == 'all':
                self._days_as_int = list(range(7))
                break

            self._days_as_int.append(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].index(day))
        
        if isinstance(self._config.upload, str):
            self._upload_reduce_by = int(self._config.upload[:-1]) / 100 * self._module._config.max_upload
        else:
            self._upload_reduce_by = self._config.upload

        if isinstance(self._config.download, str):
            self._download_reduce_by = int(self._config.download[:-1]) / 100 * self._module._config.max_download
        else:
            self._download_reduce_by = self._config.download
        
        self.timezone = datetime.now(timezone.utc).astimezone().tzinfo
        logger.info("<ScheduleThread> Using timezone: %s", self.timezone)

    
    def calculate_next_occurrence(self, hour: int, minute: int) -> datetime:
        now = datetime.now(self.timezone)
        today = now.date()
        
        for day_offset in range(8):  # Search up to 7 days ahead
            candidate_date = today + timedelta(days=day_offset)
            if candidate_date.weekday() in self._days_as_int:
                candidate_time = datetime.combine(candidate_date, time(hour, minute), tzinfo=self.timezone)
                if candidate_time > now:
                    return candidate_time

        # If all else fails, raise an exception (should not happen with a valid _days_as_int)
        raise ValueError("No valid next occurrence found within the next week.")
    

    def set_reduction(self):
        "Set the reduction value for the module, and dispatches an update event."

        reduction_value = self._module.reduction_value_dict.get(self._config)
        if reduction_value == (self._upload_reduce_by, self._download_reduce_by):
            return

        self._module.reduction_value_dict[self._config] = (self._upload_reduce_by, self._download_reduce_by)
        self._module._update_event.set()


    def remove_reduction(self):
        "Remove the reduction value for the module, and dispatches an update event."

        reduction_value = self._module.reduction_value_dict.get(self._config)
        if reduction_value is None:
            return

        self._module.reduction_value_dict.pop(self._config)
        self._module._update_event.set()

    
    def run(self) -> None:
        while True:
            next_start_occurrence = self.calculate_next_occurrence(self._start_hour, self._start_minute)
            next_end_occurrence = self.calculate_next_occurrence(self._end_hour, self._end_minute)
            
            logger.debug(f"<ScheduleThread> Next start occurrence: {next_start_occurrence}, Next end occurrence: {next_end_occurrence}")

            if next_start_occurrence > next_end_occurrence:
                # currently between the start and end time
                self.set_reduction()

                sleeping_time = (next_end_occurrence - datetime.now(tz=self.timezone)).total_seconds()
                logger.debug(f"<ScheduleThread> start>end, Sleeping for {sleeping_time} seconds")

                sleep(sleeping_time)
            
            elif next_start_occurrence < next_end_occurrence:
                # currently outside the start and end time
                self.remove_reduction()

                sleeping_time = (next_start_occurrence - datetime.now(tz=self.timezone)).total_seconds()
                logger.debug(f"<ScheduleThread> start<end, Sleeping for {sleeping_time} seconds")

                sleep(sleeping_time)
            
            else:
                # start and end time are the same
                logger.debug("<ScheduleThread> start=end?")
                raise Exception("Start and end time are the same, this is forbidden.")
