# Erebus customizations by Peyman Yousefi; original RoboCupJunior credits retained.
from urllib.parse import unquote
from ConsoleLog import Console


class Config():
    """Holds data for the settings configuration of Erebus
    """

    def __init__(self, config_data: list[str], path: str):
        """Initialises config settings data

        Args:
            config_data (list[str]): List of config settings
            path (str): Path to config.txt file
        """
        # config_data format
        # [0]: Keep controller/robot files
        # [1]: Disable auto LoP
        # [2]: HTML replay recording (no video recording)
        # [3]: Automatic camera
        # [4]: Keep remote
        # [5]: Debug enabled
        # [6]: Docker path
        # [7..8]: Optional controller-file reload and source path
        # [9]: Reserved former JSON-path field
        # [10]: Show head-up display (defaults on for existing configs)
        # [11]: Generate map review (defaults off)

        self.path: str = path

        self.keep_controller: bool = bool(int(config_data[0]))
        self.disable_lop: bool = bool(int(config_data[1]))
        self.recording: bool = bool(int(config_data[2]))
        self.automatic_camera: bool = bool(int(config_data[3]))
        
        # Keep v23 compatibility
        self.keep_remote: bool = False  
        self.docker_path: str = ""

        if len(config_data) >= 5:
            self.keep_remote = bool(int(config_data[4]))
            Console.update_debug_mode(bool(int(config_data[5])))
            self.docker_path = str(config_data[6])
            if self.docker_path.startswith("uri:"):
                self.docker_path = unquote(self.docker_path[4:])

        # Manual reload is opt-in; old seven-field settings default to off.
        self.auto_reload_sources = len(config_data) > 7 and config_data[7] == '1'
        self.controller_source = unquote(config_data[8]) if len(config_data) > 8 else ''

        self.show_hud = len(config_data) <= 10 or config_data[10] != '0'

        # Optional review/export of an accepted map; independent of recording.
        self.map_review = len(config_data) > 11 and config_data[11] == '1'
