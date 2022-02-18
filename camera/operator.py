
class CameraOperator():

    def __init__(self, camera, log) -> None:
        self.camera = camera
        self.log = log

    def set_privacy_mode(self, mode):
        self.log.info(f"set_privacy_mode {mode}")
        self.camera.command(f"configManager.cgi?action=setConfig&LeLensMask[0].Enable={str(mode).lower()}")

    def set_absolute_position(self, horizonal_angle, vertical_angle, zoom):
        self.log.info(f"set_absolute_position {horizonal_angle},{vertical_angle},{zoom}")
        self.camera.ptz_control_command(action="start", code="PositionABS", arg1=horizonal_angle, arg2=vertical_angle, arg3=zoom)
