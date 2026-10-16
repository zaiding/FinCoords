"""
9ellet maydar code:)
-------------------
Selects a point on a vector point layer and instantly displays its coordinates in EPSG:4326 (latitude/longitude) in a small window, with buttons to copy each value to the clipboard. Developped to be used in GEMS to add manholes.
"""
class CoordPickerDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent, Qt.Tool)
        self.iface = iface
        self.setWindowTitle("Fin Coordinates (EPSG:4326)")
        self.setMinimumWidth(320)

        self.lat_edit = QLineEdit()
        self.lon_edit = QLineEdit()
        for e in (self.lat_edit, self.lon_edit):
            e.setReadOnly(True)

        self.status_label = QLabel("Select a point on the active layer")
        self.status_label.setWordWrap(True)

        lat_row = QHBoxLayout()
        lat_row.addWidget(QLabel("Latitude :"))
        lat_row.addWidget(self.lat_edit)
        btn_lat = QPushButton("Copy")
        btn_lat.clicked.connect(lambda: self.copy_text(self.lat_edit.text()))
        lat_row.addWidget(btn_lat)

        lon_row = QHBoxLayout()
        lon_row.addWidget(QLabel("Longitude :"))
        lon_row.addWidget(self.lon_edit)
        btn_lon = QPushButton("Copy")
        btn_lon.clicked.connect(lambda: self.copy_text(self.lon_edit.text()))
        lon_row.addWidget(btn_lon)

        btn_both = QPushButton("Copy Latitude, Longitude")
        btn_both.clicked.connect(self.copy_both)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addLayout(lat_row)
        layout.addLayout(lon_row)
        layout.addWidget(btn_both)
        self.setLayout(layout)

        self._connected_layer = None
        self._signals_connected = False
        # Plus de connexion ici : elle est faite dans showEvent

    def showEvent(self, event):
        # Reconnecte les signaux à chaque affichage de la fenêtre
        if not self._signals_connected:
            self.iface.currentLayerChanged.connect(self.on_layer_changed)
            self._signals_connected = True
        self.on_layer_changed(self.iface.activeLayer())
        super().showEvent(event)

    def _disconnect_layer(self):
        if self._connected_layer is not None:
            try:
                self._connected_layer.selectionChanged.disconnect(self.update_coords)
            except (TypeError, RuntimeError):
                pass
            self._connected_layer = None

    def _disconnect_signals(self):
        self._disconnect_layer()
        if self._signals_connected:
            try:
                self.iface.currentLayerChanged.disconnect(self.on_layer_changed)
            except (TypeError, RuntimeError):
                pass
            self._signals_connected = False

    def copy_text(self, text):
        QApplication.clipboard().setText(text)

    def copy_both(self):
        self.copy_text(f"{self.lat_edit.text()}, {self.lon_edit.text()}")

    def on_layer_changed(self, layer):
        self._disconnect_layer()

        if (
            layer is not None
            and layer.type() == layer.VectorLayer
            and layer.geometryType() == QgsWkbTypes.PointGeometry
        ):
            layer.selectionChanged.connect(self.update_coords)
            self._connected_layer = layer
            self.update_coords()
        else:
            self.status_label.setText("The active layer is not a vector point layer")
            self.lat_edit.clear()
            self.lon_edit.clear()

    def update_coords(self, *args):
        layer = self._connected_layer
        if layer is None:
            return

        selected = layer.selectedFeatures()
        if not selected:
            self.status_label.setText("No feature is selected")
            self.lat_edit.clear()
            self.lon_edit.clear()
            return

        source_crs = layer.crs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

        geom = selected[0].geometry()
        if geom is None or geom.isEmpty():
            self.status_label.setText("Empty geometry")
            return

        if QgsWkbTypes.isMultiType(geom.wkbType()):
            pt = geom.asMultiPoint()[0]
        else:
            pt = geom.asPoint()

        pt_4326 = transform.transform(pt)
        lon, lat = pt_4326.x(), pt_4326.y()

        self.lat_edit.setText(f"{lat:.8f}")
        self.lon_edit.setText(f"{lon:.8f}")

        extra = ""
        if len(selected) > 1:
            extra = f" ({len(selected)} selected features, only 1st is shown)"
        self.status_label.setText(f"Selected point{extra}")

    def closeEvent(self, event):
        self._disconnect_signals()
        event.accept()
