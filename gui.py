import sys
from PyQt5.QtWidgets import QApplication, QWidget, QSpinBox, QGridLayout, QLabel, QPushButton,QHBoxLayout
from PyQt5.QtCore import Qt


def run_clicked():
    print("RUN")

def stop_clicked():
    print("STOP")

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("CONTAINER DEPLOYMENT")
window.setGeometry(100, 100, 600, 400)

gridLayout = QGridLayout()
gridLayout.setContentsMargins(30, 30, 30, 30)  # Top, Left, Bottom, Right margins
gridLayout.setVerticalSpacing(2)
gridLayout.setHorizontalSpacing(2)

#switches box
switchesLayout = QHBoxLayout()
switches = QSpinBox()
switchesLayout.addWidget(QLabel("Switches: "))
switchesLayout.addWidget(switches)
switchesLayout.setContentsMargins(5, 0, 5, 0)

#hosts box
hostsLayout = QHBoxLayout()
hosts = QSpinBox()
hostsLayout.addWidget(QLabel("Hosts: "))
hostsLayout.addWidget(hosts)
hostsLayout.setContentsMargins(5, 0, 5, 0)

# Add the HBoxLayouts to the grid
gridLayout.addLayout(switchesLayout, 0, 0)
gridLayout.addLayout(hostsLayout, 0, 1)
generate = QPushButton("Generate Topology")
gridLayout.addWidget(generate, 1, 0, 1, 2,Qt.AlignHCenter)  # def addLayout (arg__1, row, column, rowSpan, columnSpan[, alignment=Qt.Alignment()])

run = QPushButton("RUN")
stop = QPushButton("STOP")
gridLayout.addWidget(run, 2, 0 , 1 ,1,Qt.AlignHCenter)
gridLayout.addWidget(stop, 2, 1 ,1, 1,Qt.AlignHCenter)


run.setFixedSize(100, 35)
stop.setFixedSize(100, 35)
generate.setFixedSize(150,50)
#gridLayout.setSpacing(15)

run.clicked.connect(run_clicked)
stop.clicked.connect(stop_clicked)


window.setLayout(gridLayout)

window.show()

sys.exit(app.exec_())