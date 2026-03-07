from dpi.utilities import DPILogger

from dpi.calibration import CalibrationLinearModelBase


class SUCalibrationLinearModel(CalibrationLinearModelBase):
    """SU Linear calibration model."""

    def __init__(self, key, amp_range, log_level=DPILogger.NOTICE):
        super().__init__(log_level)

        self.amp_channel = key
        self.amp = amp_range

        self.scale = 1 / 10.0 ** (self.amp)

        self._logger.debug(self._get_model_description())

    def _get_model_description(self):
        return f"SU Calibration Linear Model (Amplifier Channel={self.amp_channel})"
