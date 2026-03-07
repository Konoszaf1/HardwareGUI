from sklearn.gaussian_process.kernels import Matern

from dpi.utilities import DPILogger

from dpi.calibration import CalibrationGPModelBase


class SUCalibrationGPModel(CalibrationGPModelBase):
    """SU Gaussian Process calibration model with symlog scaling."""

    def __init__(self, key, amp_range, lin_thresh=0.5, kernel=Matern(length_scale=1, nu=0.5), min_score=1e-14, grad_thresh=50e-6, log_level=DPILogger.NOTICE):
        super().__init__(lin_thresh, kernel, min_score, grad_thresh, log_level)

        self.amp_channel = key
        self.amp = amp_range

        self.scale = 1 / 10.0 ** (self.amp)

        self._logger.debug(self._get_model_description())

    def _get_model_description(self):
        return f"SU Calibration GP Model (Amplifier Channel={self.amp_channel})"
