from loads import *
from client.loads import *
import app_manager
import time
import client.client_manager as client


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = app_manager.Window()
    window.connectLayout()
    window.show()

    sys.exit(app.exec())

   
     