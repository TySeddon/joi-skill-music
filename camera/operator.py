
class CameraOperator():

    def __init__(self, camera) -> None:
        self.camera = camera

    def set_privacy_mode(self, mode):
        self.camera.command(f"configManager.cgi?action=setConfig&LeLensMask[0].Enable={str(mode).lower()}")

    def set_absolute_position(self, horizonal_angle, vertical_angle, zoom):
        self.camera.ptz_control_command(action="start", code="PositionABS", arg1=horizonal_angle, arg2=vertical_angle, arg3=zoom)
