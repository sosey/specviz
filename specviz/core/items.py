from itertools import cycle

import pyqtgraph as pg
from astropy.units import spectral, spectral_density
from qtpy.QtCore import Property, Qt, Signal
from qtpy.QtGui import QStandardItem

flatui = cycle(["#000000", "#9b59b6", "#3498db", "#95a5a6", "#e74c3c",
                "#34495e", "#2ecc71"])


class DataItem(QStandardItem):
    NameRole = Qt.UserRole + 1
    IdRole = Qt.UserRole + 2
    DataRole = Qt.UserRole + 3

    def __init__(self, name, identifier, data, unit=None,
                 spectral_axis_unit=None, *args, **kwargs):
        super(DataItem, self).__init__(*args, **kwargs)

        self.setData(name, self.NameRole)
        self.setData(identifier, self.IdRole)
        self.setData(data, self.DataRole)

        self.setCheckable(True)

    @property
    def identifier(self):
        return self.data(self.IdRole)

    @Property(str)
    def name(self):
        return self.data(self.NameRole)

    @name.setter
    def name(self, value):
        self.setData(value, self.NameRole)

    @Property(list)
    def flux(self):
        return self.data(self.DataRole).flux

    @Property(list)
    def spectral_axis(self):
        return self.data(self.DataRole).spectral_axis

    def set_data(self, data):
        """
        Updates the stored :class:`~specutils.Spectrum1D` data values.
        """
        self.setData(data, self.DataRole)

    @property
    def spectrum(self):
        return self.data(self.DataRole)


class PlotDataItem(pg.PlotDataItem):
    data_unit_changed = Signal(str)
    spectral_axis_unit_changed = Signal(str)
    color_changed = Signal(str)
    width_changed = Signal(int)
    visibility_changed = Signal(bool)

    def __init__(self, data_item, color=None, *args, **kwargs):
        super(PlotDataItem, self).__init__(*args, **kwargs)

        self._data_item = data_item
        self._data_unit = self._data_item.flux.unit.to_string()
        self._spectral_axis_unit = self._data_item.spectral_axis.unit.to_string()
        self._color = color or next(flatui)
        self._width = 1
        self._visible = False

        # Set data
        self.set_data()
        self._update_pen()

        # Connect slots to data item signals
        self.data_unit_changed.connect(self.set_data)
        self.spectral_axis_unit_changed.connect(self.set_data)

        # Connect to color signals
        self.color_changed.connect(self._update_pen)
        self.width_changed.connect(self._update_pen)
        self.visibility_changed.connect(self._update_pen)

    def _update_pen(self, *args):
        if self.visible:
            try:
                color = float(self.color)
            except ValueError:
                color = self.color

            self.setPen(color=color, width=float(self.width))
        else:
            self.setPen(None)

    @property
    def data_item(self):
        return self._data_item

    @Property(str, notify=data_unit_changed)
    def data_unit(self):
        return self._data_unit

    @data_unit.setter
    def data_unit(self, value):
        self._data_unit = value
        self.data_unit_changed.emit(self._data_unit)

    def are_units_compatible(self, spectral_axis_unit, data_unit):
        return self.is_data_unit_compatible(data_unit) and \
            self.is_spectral_axis_unit_compatible(spectral_axis_unit)

    def is_data_unit_compatible(self, unit):
        return (self.data_item.flux.unit == "" or
                unit is not None and
                self.data_item.flux.unit.is_equivalent(
                    unit, equivalencies=spectral_density(self.spectral_axis)))

    def is_spectral_axis_unit_compatible(self, unit):
        return (self.data_item.spectral_axis.unit == "" or
                unit is not None and
                self.data_item.spectral_axis.unit.is_equivalent(
                    unit, equivalencies=spectral()))

    @Property(str, notify=spectral_axis_unit_changed)
    def spectral_axis_unit(self):
        return self._spectral_axis_unit

    @spectral_axis_unit.setter
    def spectral_axis_unit(self, value):
        self._spectral_axis_unit = value
        self.spectral_axis_unit_changed.emit(self._spectral_axis_unit)

    def reset_units(self):
        self.data_unit = self.data_item.flux.unit.to_string()
        self.spectral_axis_unit = self.data_item.spectral_axis.unit.to_string()

    @Property(list)
    def flux(self):
        return self._data_item.flux.to(self.data_unit,
                                       equivalencies=spectral_density(
                                           self.spectral_axis)).value

    @property
    def spectral_axis(self):
        return self._data_item.spectral_axis.to(self.spectral_axis_unit,
                                                equivalencies=spectral()).value

    @Property(str, notify=color_changed)
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self.color_changed.emit(self._color)
        self.data_item.emitDataChanged()

    @Property(int, notify=width_changed)
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value
        self.width_changed.emit(self._width)
        self.data_item.emitDataChanged()

    @property
    def zorder(self):
        return self.zValue()

    @zorder.setter
    def zorder(self, value):
        self.setZValue(value)
        self.data_item.emitDataChanged()

    @Property(bool, notify=visibility_changed)
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value
        self.visibility_changed.emit(self._visible)

    def update_data(self):
        # Replot data
        self.setData(self.spectral_axis, self.flux, connect="finite")

    def set_data(self):
        self.setData(self.spectral_axis, self.flux, connect="finite")


class ModelItem(QStandardItem):
    DataRole = Qt.UserRole + 2

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setData(model.__class__.name, Qt.DisplayRole)
        self.setData(model, self.DataRole)


class ParameterItem(QStandardItem):
    DataRole = Qt.UserRole + 2
    UnitRole = Qt.UserRole + 3

    def __init__(self, parameter, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setData(parameter.name, Qt.DisplayRole)
        self.setData(parameter.value, self.DataRole)
        self.setData(parameter.unit, self.UnitRole)