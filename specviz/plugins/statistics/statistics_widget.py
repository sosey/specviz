import os
import numpy as np

from astropy import units as u

from specutils.spectra.spectral_region import SpectralRegion
from specutils.analysis.snr import snr

from qtpy.QtWidgets import QWidget
from qtpy.uic import loadUi
from qtpy.QtGui import QIcon

from ...core.items import PlotDataItem
from ...utils import UI_PATH
from ...utils.helper_functions import format_float_text
from ...core.plugin import Plugin, plugin_bar


"""
The next three functions are place holders while specutils is updated to handle
these computations internally. They will be moved into the StatisticsWidget
once they are updated.
"""
def check_unit_compatibility(spec, region):
    spec_unit = spec.spectral_axis.unit
    if region.lower is not None:
        region_unit = region.lower.unit
    elif region.upper is not None:
        region_unit = region.upper.unit
    else:
        return False
    return spec_unit.is_equivalent(region_unit)


def clip_region(spectrum, region):
    # If the region is out of data range return None:
    if region.lower > spectrum.spectral_axis.max() or \
            region.upper < spectrum.spectral_axis.min():
        return None

    # Clip region:
    if region.lower < spectrum.spectral_axis.min():
        region.lower = spectrum.spectral_axis.min()
    if region.upper > spectrum.spectral_axis.max():
        region.upper = spectrum.spectral_axis.max()
    return region


def compute_stats(spectrum):
    """
    Compute basic statistics for a spectral region.
    Parameters
    ----------
    spectrum : `~specutils.spectra.spectrum1d.Spectrum1D`
    region: `~specutils.utils.SpectralRegion`
    """
    flux = spectrum.flux
    mean = flux.mean()
    rms = np.sqrt(flux.dot(flux) / len(flux))
    return {'mean': mean,
            'median': np.median(flux),
            'stddev': flux.std(),
            'rms': rms,
            'snr': mean / rms,  # snr(spectrum=spectrum),
            'total': np.trapz(flux),
            'maxval': flux.max(),
            'minval': flux.min()}


@plugin_bar("Statistics", icon=QIcon(":/icons/012-file.svg"))
class StatisticsWidget(QWidget, Plugin):
    """
    This widget controls the statistics box. It is responsible for calling
    stats computation functions and updating the stats widget. It only takes
    the owner workspace's current data item and selected region for stats
    computations. The stats box can be updated by calling the update_statistics
    function.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_spectrum = None  # Current `Spectrum1D`
        self.stats = None  # dict with stats

        self._init_ui()

        self.workspace.current_item_changed.connect(self.update_statistics)
        # When the current subwindow changes, update the stat widget
        self.workspace.mdi_area.subWindowActivated.connect(self.update_statistics)
        # When current item changes, update the stat widget
        self.workspace.current_item_changed.connect(self.update_statistics)
        # When selection changes, update the stat widget
        self.workspace.current_selected_changed.connect(self.update_statistics)
        # When new plot window is added, connect signals
        self.workspace.plot_window_added.connect(self._connect_plot_window)

        # Connect any currently open plot windows
        for plot_window in self.plot_windows:
            self._connect_plot_window(plot_window)

    def _init_ui(self):
        loadUi(os.path.abspath(
               os.path.join(os.path.dirname(__file__), "statistics.ui")), self)

        # A dict of display `QLineEdit` and their stat keys:
        self.stat_widgets = {
            'minval': self.min_val_line_edit,
            'maxval': self.max_val_line_edit,
            'mean': self.mean_line_edit,
            'median': self.median_line_edit,
            'stddev': self.std_dev_line_edit,
            'rms': self.rms_line_edit,
            'snr': self.snr_line_edit,
            'total': self.count_total_line_edit
        }

    def _connect_plot_window(self, plot_window):
        plot_window.plot_widget.plot_added.connect(self.update_statistics)
        plot_window.plot_widget.plot_removed.connect(self.update_statistics)
        plot_window.plot_widget.roi_moved.connect(self.update_statistics)
        plot_window.plot_widget.roi_removed.connect(self.update_statistics)

    def set_status(self, message):
        self.status_display.setPlainText(message)

    def clear_status(self):
        self.set_status("")

    def _update_stat_widgets(self, stats):
        """
        Clears all widgets then fills in
        the available stat values.
        Parameters
        ----------
        stats: dict
            Key: key in `StatisticsWidget.stat_widgets`.
            Value: float value to display
        """
        self._clear_stat_widgets()
        if stats is None:
            return
        for key in stats:
            if key in self.stat_widgets:
                text = format_float_text(stats[key])
                self.stat_widgets[key].setText(text)

    def _clear_stat_widgets(self):
        """
        Clears all widgets in `StatisticsWidget.stat_widgets`
        """
        for key in self.stat_widgets:
            self.stat_widgets[key].setText("")

    @staticmethod
    def pos_to_spectral_region(pos):
        """
        Vet input region position and construct
        a `~specutils.utils.SpectralRegion`.
        Parameters
        ----------
        pos : `~astropy.units.Quantity`
            A tuple `~astropy.units.Quantity` with
            (min, max) range of roi.

        Returns
        -------
        None or `~specutils.utils.SpectralRegion`
        """
        if not isinstance(pos, u.Quantity):
            return None
        elif pos.unit == u.Unit("") or \
                pos[0] == pos[1]:
            return None
        elif pos[0] > pos[1]:
            pos = [pos[1], pos[0]] * pos.unit
        return SpectralRegion(*pos)

    def _get_workspace_region(self):
        """Get current widget region."""
        pos = self.selected_region_bounds

        if pos is not None:
            return self.pos_to_spectral_region(pos)

    def _workspace_has_region(self):
        """True if there is an active region"""
        return self.selected_region is not None

    def _get_target_name(self):
        """Gets name of data and region selected"""
        current_item = self.workspace.current_item
        region = self._get_workspace_region()
        if current_item is not None:
            if isinstance(current_item, PlotDataItem):
                current_item = current_item.data_item
        if current_item is None or not hasattr(current_item, "name"):
            return ""
        if region is None:
            return "Data: {0}".format(current_item.name)
        else:
            return "Data: {0}\n" \
                   "Region Max: {1:0.5g}\n" \
                   "Region Min: {2:0.5g}".format(current_item.name,
                                                 region.upper,
                                                 region.lower)

    def clear_statistics(self):
        self._clear_stat_widgets()
        self.stats = None

    def update_statistics(self):
        if self.workspace is None or self.plot_item is None:
            return self.clear_statistics()

        # If the plot item is not visible, don't bother updating stats
        if not self.plot_item.visible:
            return self.clear_statistics()

        spec = self.data_item.spectrum if self.data_item is not None else None
        spectral_region = self._get_workspace_region()

        self._current_spectrum = spec

        # Check for issues and extract
        # region from input spectra:
        if spec is None:
            self.set_status("No data selected.")
            return self.clear_statistics()
        if spectral_region is not None:
            if not check_unit_compatibility(spec, spectral_region):
                self.set_status("Region units are not compatible with "
                                "selected data's spectral axis units.")
                return self.clear_statistics()
            spectral_region = clip_region(spec, spectral_region)
            if spectral_region is None:
                self.set_status("Region out of bound.")
                return self.clear_statistics()
            try:
                idx1, idx2 = spectral_region.to_pixel(spec)
                if idx1 == idx2:
                    self.set_status("Region over single value.")
                    return self.clear_statistics()
                spec = spectral_region.extract(spec)
            except ValueError as e:
                self.set_status("Region could not be extracted "
                                "from target data.")
                return self.clear_statistics()
        elif self._workspace_has_region():
            self.set_status("Region has no units")
            return self.clear_statistics()

        # Compute stats and update widget:
        self.stats = compute_stats(spec)
        self._update_stat_widgets(self.stats)
        self.set_status(self._get_target_name())

    def update_signal_handler(self, *args, **kwargs):
        """
        Universal signal handler for update calls.
        """
        self.update_statistics()

