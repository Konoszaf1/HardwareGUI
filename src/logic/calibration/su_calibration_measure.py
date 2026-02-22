"""SU Calibration Measurement class.

Ported from /measdata/dpi/samplingunit/python/dev/calibration_measure.py
All imports use proper dpi package paths — no device_scripts symlinks.
"""

import time

import numpy as np
import pandas as pd
from tqdm import tqdm

from dpi import DPISamplingUnit, DPISourceMeasureUnit
from dpi.calibration import CalibrationMeasureBase, Keithley
from dpi.unit import DPIEpromEntry_new as DPIEpromEntry
from dpi.utilities import DPILogger


class SUCalibrationMeasure(CalibrationMeasureBase):
    """Calibration measurement for Sampling Unit.

    Extends CalibrationMeasureBase to perform voltage calibration measurements
    using a Keithley source meter as reference instrument.
    """

    def __init__(
        self,
        keithley_ip,
        smu_serial=None,
        smu_int=None,
        su_serial=None,
        su_int=None,
        log_level=DPILogger.VERBOSE,
    ):
        self.smu_serial = smu_serial
        self.smu_int = smu_int
        self.su_serial = su_serial
        self.su_int = su_int

        super().__init__(keithley_ip, log_level)

        self._logger.verbose(f"amp_channels: {self.ampchannels}")
        self._logger.verbose(f"amp_ranges: {self.ampranges}")

    def _init_reference_instrument(self, instrument_ip, log_level):
        self.keithley = Keithley(instrument_ip, log_level)

    def _init_device(self):
        # Connect to SMU
        if self.smu_serial is None or self.smu_int is None:
            self.smu = DPISourceMeasureUnit(autoinit=True)
        else:
            self.smu = DPISourceMeasureUnit(serial=self.smu_serial, interface=self.smu_int)

        # Connect to SU
        if self.su_serial is None or self.su_int is None:
            self.su = DPISamplingUnit(autoinit=True)
        else:
            self.su = DPISamplingUnit(serial=self.su_serial, interface=self.su_int)

        self.device_serial = self.su._DPIIO_Legacy__dev.getSerial()

    def _get_device_info(self):
        return self.su.deviceInfoJson() + self.smu.deviceInfoJson()

    def _get_measurement_channels(self):
        eprom = self.su.get_eeprom_interface()
        keys = eprom.keys()

        self.ampchannels = keys[:-1]
        self.ampranges = [np.abs(eprom[k]["gain"]) for k in keys][:-1]

    def _calculate_total_measurements(self, channels_info, measurement_values):
        return len(channels_info) * len(measurement_values)

    def prepare_measure(self, tmeasure, tsample, amp_channel):
        # SMU: set initial state
        self.smu.smu_bus_enable(0, DPISourceMeasureUnit.SMU_CONTROL_BUS_NONE)
        self.smu.enable(0)
        self.smu.vguard_to_gnd()
        # SMU: set IV converter to GND
        self.smu.ivconverter_setreference("GND")

        # SMU: highpass
        self.smu.highpass_disable()

        # SMU: Set to Voltage mode
        self.smu.iin_to_su()

        # SU: init
        self.su.setPath(source="VIN", ac=0, adc=None, amp=amp_channel)
        self.su.transientSampling_init(
            measurementTime=tmeasure,
            trigger="none",
            samplingmode=("linear", tsample),
            measurementDelay=0.0,
            resetAverageCounterAfterTime=1e10,
            adcmaster=1,
        )

    def measure(self, tmeasure):
        self.su.transientSampling_start()
        time.sleep(tmeasure + 0.1)

        voltagesamples, (timestamps, timestampssplit) = self.su.transientSampling_readData()

        return timestamps, voltagesamples

    def measure_single_range(
        self,
        amp_channel,
        voltage_values,
        progress_bar=None,
        on_point_measured=None,
    ):
        """Perform a measurement for a single measurement range.

        Parameters
        ----------
        amp_channel : str
            The amplifier channel to measure.
        voltage_values : list
            List of voltage values, relative to current and pa range.
        progress_bar : tqdm.tqdm or None, optional
            An optional tqdm progress bar object.
        on_point_measured : callable or None, optional
            Called after each measurement point with a dict containing
            ``series``, ``x`` (reference voltage), ``y`` (mean measured),
            and ``v_set``.
        """
        own_bar = False

        # Create progress bar
        if progress_bar is None:
            total = len(voltage_values)
            progress_bar = tqdm(total=total, desc="Measurement Progress")
            own_bar = True

        try:
            amp_index = self.ampchannels.index(amp_channel)
        except ValueError:
            self._logger.error("IV Channel does not exist!")
            return

        try:
            if "AMP01" == amp_channel:
                channel_val = 10.0
            if "AMP1" == amp_channel:
                channel_val = 1.0
            if "AMP2" == amp_channel:
                channel_val = 0.1
                self._logger.warning("Care measurement values are reseted!")
                voltage_values = self.prepare_measurement_values(
                    max_value=2.0, decades=7, delta_log=1 / 2, delta_lin=1 / 6
                )
        except ValueError:
            self._logger.error("Amplifier does not exist!")
            return

        amprange = self.ampranges[amp_index]

        # tmeasure depends on bandwidth of the amplifier
        tmeasure = 0.1
        tsample = 1e-4

        # prepare measurement
        self.prepare_measure(tmeasure, tsample, amp_channel=channel_val)

        # calculate the adjusted measurement currents
        voltage_values_array = np.array(voltage_values)
        meas_voltages = voltage_values_array * 1 / channel_val

        for meas_voltage in meas_voltages:
            # keithley is in source mode, a positive current flows out of the keithley
            reference_voltage = self.keithley.set_v(meas_voltage)

            t, samples = self.measure(tmeasure)

            self._logger.debug(
                f"Measuring in amp channel {amp_channel}, v_set {meas_voltage}, i_ref{reference_voltage}"
            )

            # store to datafile
            df = pd.DataFrame({"time": t, "voltage": samples})
            df.attrs["unit"] = ["s", "V"]
            df.attrs["v_set"] = meas_voltage
            df.attrs["v_ref"] = reference_voltage
            df.attrs["amp_channel"] = amp_channel
            df.attrs["amp_range"] = amprange
            df.attrs["name"] = f"amp={df.attrs['amp_channel']} v_set={df.attrs['v_set']:.3e}"
            df.attrs["temperature_smu"] = self.smu.get_temperature()
            df.attrs["temperature_su"] = self.su.getTemperature()

            self.data.append(df)

            if on_point_measured is not None:
                on_point_measured(
                    {
                        "series": amp_channel,
                        "x": float(reference_voltage),
                        "y": float(np.mean(samples)),
                        "v_set": float(meas_voltage),
                    }
                )

            progress_bar.update(1)

        # Close progress bar
        if own_bar:
            progress_bar.n = progress_bar.total
            progress_bar.close()

    def measure_all_ranges(self, voltage_values, progress_bar=None, on_point_measured=None):
        """Measure all amplifier ranges.

        Parameters
        ----------
        voltage_values : list
            Voltage setpoints to sweep.
        progress_bar : tqdm.tqdm or None, optional
            Shared progress bar instance.
        on_point_measured : callable or None, optional
            Forwarded to :meth:`measure_single_range`.
        """
        own_bar = False

        # Create progress bar
        if progress_bar is None:
            total = len(self.ampchannels) * len(voltage_values)
            progress_bar = tqdm(total=total, desc="Measurement Progress")
            own_bar = True

        # Measure calibration values
        for amp_channel in self.ampchannels:
            progress_bar.set_description(f"AMP: {amp_channel}, VL: {len(voltage_values)}")
            self.measure_single_range(
                amp_channel,
                voltage_values,
                progress_bar,
                on_point_measured,
            )

        # Close progress bar
        if own_bar:
            progress_bar.n = progress_bar.total
            progress_bar.close()

    def cleanup(self):
        """Clean up SMU state after measurement."""
        self.smu.smu_bus_enable(0, DPISourceMeasureUnit.SMU_CONTROL_BUS_NONE)
        self.smu.enable(0)
        self.smu.vguard_to_gnd()
        self.smu.highpass_disable()
