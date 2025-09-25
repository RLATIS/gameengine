import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFrame, QSplitter, QSplitterHandle,
    QLabel, QWidget, QMenu, QListWidget
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QIntValidator, QKeyEvent, QPainter
from PyQt6.QtWidgets import QListWidgetItem, QLineEdit, QVBoxLayout, QComboBox, QFormLayout

assetspath = 'assets'

if not os.path.exists(assetspath):
    os.makedirs(assetspath)

folderimgassetpath = os.path.join(assetspath, "FOLDER.png")
scriptimgassetpath = os.path.join(assetspath, "SCRIPT.png")
matimgassetpath = os.path.join(assetspath, "MATERIAL.png")
audioimgassetpath = os.path.join(assetspath, "AUDIO.png")
photoimgassetpath = os.path.join(assetspath, "IMAGE.png")

ICONSIZE = 64

class Viewport(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: black;")
        self.objects = []  # store drawable objects

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Example: draw objects
        for obj in self.objects:
            painter.setBrush(obj['color'])
            painter.drawRect(obj['x'], obj['y'], obj['w'], obj['h'])

        painter.end()

class CustomSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.parent().reset_sizes()
        super().mousePressEvent(event)

class CustomSplitter(QSplitter):
    def __init__(self, orientation, parent=None, reset_sizes=None):
        super().__init__(orientation, parent)
        self.reset_sizes_list = reset_sizes
        self.setHandleWidth(2)

    def createHandle(self):
        return CustomSplitterHandle(self.orientation(), self)

    def reset_sizes(self):
        if self.reset_sizes_list:
            self.setSizes(self.reset_sizes_list)

class GameEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        version = 0
        self.setWindowTitle(f"Engine - v{version}")

        self.undo_stack = []
        self.redo_stack = []
        self.undo_timer = QTimer()
        self.undo_timer.timeout.connect(self.undo)
        self.redo_timer = QTimer()
        self.redo_timer.timeout.connect(self.redo)

        self.undo_delay = 500  # ms between repeats when holding

        # Menu bar
        menu = self.menuBar()
        opsettingsbutton = QAction("&Open Project Settings", self)
        opsettingsbutton.triggered.connect(self.openprojectsettings)
        editmenu = menu.addMenu("&Settings")
        editmenu.addAction(opsettingsbutton)
        editmenu.addSeparator()

        filemenu = menu.addMenu("&File")

        # Left panel
        self.left = QWidget()
        self.leftlayout = QFormLayout()
        self.left.setLayout(self.leftlayout)
        self.left.setStyleSheet("background-color: white; border: 1px solid black;")

        # Right panel
        self.right = QWidget()
        self.rightlayout = QFormLayout()
        self.right.setLayout(self.rightlayout)
        self.right.setStyleSheet("background-color: white; border: 1px solid black;")

        self.left.setMinimumWidth(200)
        self.right.setMinimumWidth(200)

        viewport = Viewport()
        viewport.setStyleSheet("border: 1px solid black;")

        # Property fields
        self.prop_name = QLineEdit()
        self.prop_type = QLineEdit()        
        self.prop_type.setReadOnly(True)
        self.prop_fileloc = QLineEdit()

        self.multipleselectedlabel = QLabel("Multiple Selected, Select one to choose individual Properties.")
        self.multipleselectedlabel.setStyleSheet("color: grey; border: none;")
        self.multipleselectedlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rightlayout.addWidget(self.multipleselectedlabel)
        self.multipleselectedlabel.hide()

        self.nothingselectedlabel = QLabel("Nothing Selected, Select an item.")
        self.nothingselectedlabel.setStyleSheet("color: grey; border: none;")
        self.nothingselectedlabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rightlayout.addWidget(self.nothingselectedlabel)
        self.nothingselectedlabel.hide()

        self.namelabel = QLabel("Name:")
        self.namelabel.setStyleSheet("border: none;")
        self.type_label = QLabel("Type:")
        self.type_label.setStyleSheet("border: none;")

        self.rightlayout.addRow(self.namelabel, self.prop_name)
        self.rightlayout.addRow(self.type_label, self.prop_type)

        self.fileloc_row_index = self.rightlayout.rowCount()
        self.rightlayout.addRow("File Location:", self.prop_fileloc)
        self.prop_fileloc.hide()
        self.prop_fileloc.editingFinished.connect(self.updatefilelocation)

        self.prop_name.editingFinished.connect(self.renamecurrentitem)

        hsplit = CustomSplitter(Qt.Orientation.Horizontal, reset_sizes=[150, 500, 200])
        hsplit.addWidget(self.left)
        hsplit.addWidget(viewport)
        hsplit.addWidget(self.right)
        hsplit.setSizes(hsplit.reset_sizes_list)

        self.bottom = QListWidget()
        self.bottom.setStyleSheet("border: 1px solid black;")
        self.bottom.setMinimumHeight(120)
        self.bottom.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bottom.customContextMenuRequested.connect(self.showassetscontextmenu)

        self.bottom.setViewMode(QListWidget.ViewMode.IconMode)
        self.bottom.setIconSize(QSize(ICONSIZE, ICONSIZE))
        self.bottom.setGridSize(QSize(100, 100))
        self.bottom.setMovement(QListWidget.Movement.Static)
        self.bottom.setSpacing(10)

        self.bottom.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.bottom.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)

        self.statuslabel = QLabel(self)
        self.statuslabel.setStyleSheet("color: gray; font-size: 12px;")
        self.statuslabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.statuslabel.setFixedHeight(20)  # small text

        self.updatestatuslabel()

        self.bottom.itemSelectionChanged.connect(self.updatestatuslabel)

        bottomcontainer = QWidget()
        bottomlayout = QVBoxLayout()
        bottomlayout.setContentsMargins(0,0,0,0)
        bottomlayout.setSpacing(0)

        bottomlayout.addWidget(self.bottom)  # assets panel
        bottomlayout.addWidget(self.statuslabel)  # status text

        bottomcontainer.setLayout(bottomlayout)

        vsplit = CustomSplitter(Qt.Orientation.Vertical, reset_sizes=[500, 320])
        vsplit.addWidget(hsplit)
        vsplit.addWidget(bottomcontainer)
        vsplit.setSizes(vsplit.reset_sizes_list)

        self.setCentralWidget(vsplit)

        self.bottom.installEventFilter(self)

        self.bottom.itemSelectionChanged.connect(self.updatestatuslabel)
        self.bottom.itemSelectionChanged.connect(self.updatepropertiespanel)
        self.bottom.itemChanged.connect(self.updatepropertiespanel)

        self.createasset("Folder", "Assets")
        self.undo_stack = []

        self.updatepropertiespanel()

    def updatestatuslabel(self):
        selectedcount = len(self.bottom.selectedItems())
        totalcount = self.bottom.count()
        
        if selectedcount > 0:
            self.statuslabel.setText(f"{selectedcount} item(s) selected")
        else:
            self.statuslabel.setText(f"{totalcount} item(s) in current folder")

    def eventFilter(self, source, event):
        if source is self.bottom:
            if event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_F2:
                    item = self.bottom.currentItem()
                    if item:
                        self.bottom.editItem(item)
                    return True

                if event.key() == Qt.Key.Key_C and (event.modifiers() & Qt.KeyboardModifier.ControlModifier): # Copy
                    selected_items = self.bottom.selectedItems()
                    if selected_items:
                        self.copied_items = [(i.text(), i.icon(), i.data(Qt.ItemDataRole.UserRole)) for i in selected_items]
                    return True
                
                if event.key() == Qt.Key.Key_V and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):  # Paste
                    if hasattr(self, "copied_items"):
                        self.bottom.clearSelection()
                        new_items = []
                        for text, icon, item_type in self.copied_items:
                            new_item = QListWidgetItem(icon, text)
                            new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsEditable)
                            new_item.setData(Qt.ItemDataRole.UserRole, item_type)
                            self.bottom.addItem(new_item)
                            new_item.setSelected(True)
                            new_items.append(new_item)
                        if new_items:
                            self.undo_stack.append(("add", new_items))
                        if self.bottom.count() > 0:
                            self.bottom.setCurrentItem(self.bottom.item(self.bottom.count() - 1))
                    return True
                
                if event.key() == Qt.Key.Key_Delete:
                    selected_items = self.bottom.selectedItems()
                    if selected_items:
                        self.deleteitem(selected_items)  
                    self.updatestatuslabel()
                    return True

                
                if event.key() == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    if not self.undo_timer.isActive():
                        self.undo()
                        self.undo_timer.start(self.undo_delay)
                    return True
                elif event.key() == Qt.Key.Key_Y and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    if not self.redo_timer.isActive():
                        self.redo()
                        self.redo_timer.start(self.undo_delay)
                    return True
            elif event.type() == event.Type.KeyRelease:
                if event.key() == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    self.undo_timer.stop()
                    return True
                elif event.key() == Qt.Key.Key_Y and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    self.redo_timer.stop()
                    return True

        return super().eventFilter(source, event)

    def openprojectsettings(self):
        self.settingswindow = QWidget()
        self.settingswindow.setWindowTitle("Project Settings")
        self.settingswindow.setGeometry(200, 200, 400, 300)
        self.settingswindow.setWindowFlags(
            self.settingswindow.windowFlags() | Qt.WindowType.Window
        )

        iconsizelabel = QLabel("Icon Size:", self.settingswindow)
        iconsizelabel.move(20, 20)

        self.iconsizeinput = QLineEdit(str(ICONSIZE), self.settingswindow)
        self.iconsizeinput.setGeometry(100, 15, 200, 25)
        self.iconsizeinput.setValidator(QIntValidator(1, 64))  

        # Update ICONSIZE when Enter pressed
        self.iconsizeinput.returnPressed.connect(self.updateiconsize)

        self.settingswindow.show()


    def updateiconsize(self):
        global ICONSIZE
        value = self.iconsizeinput.text()
        if value.isdigit():
            ICONSIZE = int(value)

            self.bottom.setIconSize(QSize(ICONSIZE, ICONSIZE)) 

    def showassetscontextmenu(self, pos):
        item = self.bottom.itemAt(pos)
        menu = QMenu()

        if item: 
            renameaction = QAction("Rename", self)
            renameaction.triggered.connect(lambda: self.bottom.editItem(item))
            menu.addAction(renameaction)

            deleteaction = QAction("Delete", self)
            deleteaction.triggered.connect(lambda: self.deleteitem(item))
            menu.addAction(deleteaction)
        else:  
            create_menu = menu.addMenu("Create")
            createscriptaction = QAction("Script", self)
            createscriptaction.triggered.connect(lambda: self.createasset("Script", "Script"))
            create_menu.addAction(createscriptaction)

            createfolderaction = QAction("Folder", self)
            createfolderaction.triggered.connect(lambda: self.createasset("Folder", "Folder"))
            create_menu.addAction(createfolderaction)

            createmataction = QAction("Material", self)
            createmataction.triggered.connect(lambda: self.createasset("Material", "Material"))
            create_menu.addAction(createmataction)

            createaudioaction = QAction("Audio", self)
            createaudioaction.triggered.connect(lambda: self.createasset("Audio", "Audio"))
            create_menu.addAction(createaudioaction)

            createimgaction = QAction("Image", self)
            createimgaction.triggered.connect(lambda: self.createasset("Image", "Image"))
            create_menu.addAction(createimgaction)

        menu.exec(self.bottom.mapToGlobal(pos))

    def updatepropertiespanel(self):
        selected = self.bottom.selectedItems()

        namelabel = self.namelabel
        namefield = self.prop_name
        typelabel = self.type_label
        typefield = self.prop_type
        filelabel = self.rightlayout.itemAt(self.fileloc_row_index, QFormLayout.ItemRole.LabelRole).widget()
        filefield = self.prop_fileloc
        shouldreturn = False

        if not selected or len(selected) >= 2:
            self.multipleselectedlabel.hide()
            namelabel.hide()
            namefield.hide()
            typelabel.hide()
            typefield.hide()
            filelabel.hide()
            filefield.hide()
            self.prop_name.clear()
            self.prop_type.clear()
            self.prop_fileloc.clear()
            shouldreturn = True
        
        if len(selected) >= 2:
            self.multipleselectedlabel.show()
            shouldreturn = True
        elif not selected:
            self.nothingselectedlabel.show()
            shouldreturn = True

        if shouldreturn:
            return

        item = selected[0]
        asset_type = item.data(Qt.ItemDataRole.UserRole)
        asset_name = item.text()

        self.nothingselectedlabel.hide()
        self.multipleselectedlabel.hide()
        namelabel.show()
        namefield.show()
        typelabel.show()
        typefield.show()
        self.prop_name.setText(asset_name)
        self.prop_type.setText(asset_type)

        if asset_type in ["Audio", "Image"]:
            fileloc = item.data(Qt.ItemDataRole.UserRole + 1) or ""
            self.prop_fileloc.setText(fileloc)
            filelabel.show()
            filefield.show()
        else:
            self.prop_fileloc.clear()
            filelabel.hide()
            filefield.hide()


    def updatefilelocation(self):
        selected = self.bottom.selectedItems()
        if not selected:
            return
        item = selected[0]
        item.setData(Qt.ItemDataRole.UserRole + 1, self.prop_fileloc.text())
            
    def renamecurrentitem(self):
        selected = self.bottom.selectedItems()
        if not selected:
            return
        item = selected[0]
        item.setText(self.prop_name.text())
        self.updatepropertiespanel()

    def createasset(self, assettype, assetname):
        items = []
        if assettype == 'Folder':
            foldericon = QIcon(str(folderimgassetpath))
            item = QListWidgetItem(foldericon, assetname)
            item.setData(Qt.ItemDataRole.UserRole, "Folder")
            items.append(item)
        elif assettype == 'Script':
            scripticon = QIcon(str(scriptimgassetpath))
            item = QListWidgetItem(scripticon, assetname)
            item.setData(Qt.ItemDataRole.UserRole, "Script")
            items.append(item)
        elif assettype == 'Material':
            maticon = QIcon(str(matimgassetpath))
            item = QListWidgetItem(maticon, assetname)
            item.setData(Qt.ItemDataRole.UserRole, "Material")
            items.append(item)
        elif assettype == 'Audio':
            audicon = QIcon(str(audioimgassetpath))
            item = QListWidgetItem(audicon, assetname)
            item.setData(Qt.ItemDataRole.UserRole, "Audio")
            item.setData(Qt.ItemDataRole.UserRole + 1, "")
            items.append(item)
        elif assettype == 'Image':
            photoicon = QIcon(str(photoimgassetpath))
            item = QListWidgetItem(photoicon, assetname)
            item.setData(Qt.ItemDataRole.UserRole, "Image")
            item.setData(Qt.ItemDataRole.UserRole + 1, "")
            items.append(item)

        for item in items:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.bottom.addItem(item)

        self.undo_stack.append(("add", items))
        self.redo_stack.clear()
        self.updatestatuslabel()

    def deleteitem(self, items):
        if not isinstance(items, list):
            items = [items]

        deleted = [(i, self.bottom.row(i)) for i in items]

        for i, _ in reversed(deleted):
            self.bottom.takeItem(self.bottom.row(i))

        self.undo_stack.append(("delete", deleted))
        self.redo_stack.clear()
        self.updatestatuslabel()


    def undo(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()

        if action[0] == "add":
            for item in action[1]:
                row = self.bottom.row(item)
                self.bottom.takeItem(row)
            self.redo_stack.append(action)

        elif action[0] == "delete":
            for item, row in action[1]:
                self.bottom.insertItem(row, item)
            self.redo_stack.append(action)

        self.updatestatuslabel()

    def redo(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()

        if action[0] == "add":
            for item in action[1]:
                self.bottom.addItem(item)
            self.undo_stack.append(action)

        elif action[0] == "delete":
            for item, _ in action[1]:
                row = self.bottom.row(item)
                self.bottom.takeItem(row)
            self.undo_stack.append(action)

        self.updatestatuslabel()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameEditor()

    window.showMaximized()

    sys.exit(app.exec())
