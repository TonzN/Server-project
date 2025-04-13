from loads import *
from client.loads import *
import app_manager2 as app_manager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = app_manager.Window()
    window.connectLayout()
    window.show()
    sys.exit(app.exec())
