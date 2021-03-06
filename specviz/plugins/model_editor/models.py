import uuid

import astropy.units as u
import numpy as np
import qtawesome as qta
from qtpy.QtCore import QSortFilterProxyModel, Qt
from qtpy.QtGui import QStandardItem, QStandardItemModel
from specutils import Spectrum1D


class ModelFittingModel(QStandardItemModel):
    def __init__(self, *args):
        super().__init__(*args)
        from astropy.modeling.models import Gaussian1D, Linear1D

        a = Gaussian1D()
        l = Linear1D()

        self.add_model(a)
        self.add_model(l)

    def add_model(self, model):
        oper_item = QStandardItem("Add")

        model_item = QStandardItem(model.__class__.name)
        model_item.setData(model, Qt.UserRole + 1)

        for para_name in model.param_names:
            # Retrieve the parameter object from the model
            parameter = getattr(model, para_name)

            # Store the name value
            param_name = QStandardItem(parameter.name)
            param_name.setData(parameter, Qt.UserRole + 1)
            param_name.setEditable(False)

            # Store the data value of the parameter
            param_value = QStandardItem("{}".format(parameter.value))
            param_value.setData(parameter.value, Qt.UserRole + 1)

            # Store the unit information
            param_unit = QStandardItem("{}".format(parameter.unit))
            param_unit.setData(parameter.unit, Qt.UserRole + 1)

            # Store the fixed state of the unit
            param_fixed = QStandardItem()
            param_fixed.setData(parameter.fixed, Qt.UserRole + 1)
            param_fixed.setCheckable(True)
            param_fixed.setEditable(False)

            model_item.appendRow([param_name, param_value, param_unit, param_fixed])

        self.appendRow([oper_item, model_item, None, None])


class ModelFittingProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, p_int, index):
        if index.row() >= 0:
            return False

        return super().filterAcceptsRow(p_int, index)