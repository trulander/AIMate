import logging
import platform
import subprocess
from PIL import Image, ImageTk, ImageGrab
import tkinter as tk

from utils.utils import is_wayland, detect_wayland_compositor

# import mss



logger = logging.getLogger(__name__)


class ScreenshotService:
    def __init__(self):
        logger.info('Initializing ScreenshotService')

    def take_screenshot(self, bbox: tuple):
        try:
            if platform.system() == "Linux" and is_wayland():
                compositor = detect_wayland_compositor()
                path = "/tmp/screenshot.png"
                if compositor == "kwin":
                    img = self.screenshot_wayland_with_spectacle(path)
                elif compositor == "sway":
                    img = self.screenshot_wayland_with_grim(path)
                else:
                    raise Exception("Неизвестный композитор Wayland или не поддерживается")
                img = self.crop_image(img, bbox)
            else:
                img = self.screenshot_windows_x11(bbox)

            return img

        except Exception as e:
            logger.error(e)
            # self.label.config(text=f"Ошибка: {e}")

    def screenshot_windows_x11(self, bbox):
        # with mss.mss() as sct:
        #     frame = np.array(sct.grab(bbox))
        #     result = frame
        return ImageGrab.grab(bbox=bbox)

    def screenshot_wayland_with_grim(self, path="/tmp/screenshot.png"):
        subprocess.run(f"grim {path}", shell=True, check=True)
        return Image.open(path)

    def screenshot_wayland_with_spectacle(self, path="/tmp/screenshot.png"):
        subprocess.run(["spectacle", "-b", "-n", "-o", path], check=True)
        return Image.open(path)

    def crop_image(self, img, bbox):
        return img.crop(bbox)






if __name__ == "__main__":
    def take_screenshot(label):
        bbox = (100, 100, 600, 500)
        img = ScreenshotService().take_screenshot(bbox)
        img_tk = ImageTk.PhotoImage(img)
        label.config(image=img_tk)
        label.image = img_tk


    def main():
        root = tk.Tk()
        label = tk.Label(root)
        label.pack()

        btn = tk.Button(root, text="Сделать скрин", command=lambda: take_screenshot(label))
        btn.pack()

        root.mainloop()
    main()
