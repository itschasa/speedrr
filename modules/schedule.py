import threading
from typing import List
from datetime import datetime, timezone
import time

from helpers.config import SpeedrrConfig, ScheduleConfig
from helpers.log_loader import logger



class ScheduleModule:
    "A module that manages schedules."

    def __init__(self, config: SpeedrrConfig, module_configs: List[ScheduleConfig], update_event: threading.Event) -> None:
        self.reduction_value_dict: dict[ScheduleConfig, float] = {}

        self._config = config
        self._module_configs = module_configs
        self._update_event = update_event
    
    
    def get_reduction_value(self) -> float:
        "How much to reduce the upload speed by, in the config's units."

        logger.info(f"<schedule> Reduction values = {'; '.join(f'{cfg.start}-{cfg.end}: {reduction}' for cfg, reduction in self.reduction_value_dict.items())}")
        return sum(self.reduction_value_dict.values())
    

    def run(self) -> None:
        "Start the schedule threads."

        logger.debug("Starting schedule module threads")
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
            self._reduce_by = int(self._config.upload[:-1]) / 100 * self._module._config.max_upload
        else:
            self._reduce_by = self._config.upload

        if isinstance(self._config.download, str):
            self._reduce_by = int(self._config.download[:-1]) / 100 * self._module._config.max_upload
        else:
            self._reduce_by = self._config.download
        
        self.timezone = datetime.now(timezone.utc).astimezone().tzinfo
        logger.info("<ScheduleThread> Using timezone: %s", self.timezone)

    
    def calculate_next_occurrence(self, hour: int, minute: int) -> datetime:
        "Calculate the next occurrence of the time specified by hour and minute."

        now = datetime.now(tz=self.timezone)
        current_day = now.weekday()
        current_hour = now.hour
        current_minute = now.minute

        if current_day in self._days_as_int and (current_hour, current_minute) < (hour, minute):
            return datetime(now.year, now.month, now.day, hour, minute, tzinfo=self.timezone)
        else:
            for day in self._days_as_int:
                if day > current_day: # if the day is in the future
                    return datetime(now.year, now.month, now.day + day - current_day, hour, minute, tzinfo=self.timezone)
            
            # gets the first available day in the next week
            return datetime(now.year, now.month, now.day + 7 - current_day + self._days_as_int[0], hour, minute, tzinfo=self.timezone)
    

    def set_reduction(self):
        "Set the reduction value for the module, and dispatches an update event."

        reduction_value = self._module.reduction_value_dict.get(self._config)
        if reduction_value == self._reduce_by:
            return

        self._module.reduction_value_dict[self._config] = self._reduce_by
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

                time.sleep(sleeping_time)
            
            elif next_start_occurrence < next_end_occurrence:
                # currently outside the start and end time
                self.remove_reduction()

                sleeping_time = (next_start_occurrence - datetime.now(tz=self.timezone)).total_seconds()
                logger.debug(f"<ScheduleThread> start<end, Sleeping for {sleeping_time} seconds")

                time.sleep(sleeping_time)
            
            else:
                # start and end time are the same
                logger.debug("<ScheduleThread> start=end?")
                raise Exception("Start and end time are the same, this is forbidden.")
