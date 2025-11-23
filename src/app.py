import time
import os
from typing import Optional

from PIL import Image
import numpy as np
from textual.app import App, ComposeResult
from textual.widgets import Static, Header, Footer

# Import the renderer from the other file
from morderngl_load import OffScreenRenderer


class ShaderRenderApp(App):
    """A Textual app that renders frames using ModernGL and displays them as colored text."""

    def __init__(
        self,
        *,
        width: int = 60,
        height: int = 50,
        fps: float = 20.0,
    ):
        """Initializes the Shader Render App.

        Args:
            width: The width for both rendering and display (in characters).
            height: The height for both rendering and display (in characters).
            fps: The target frames per second for rendering.
        """
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self.renderer: Optional[OffScreenRenderer] = None
        self.start_time = time.time()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("Initializing renderer...", id="video_display")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Ensure dummy shader files exist for the example to run.
        dummy_vert_path = "src/shaders/dummy.vert"
        raymarching_frag_path = "src/shaders/rayMarching.frag"
        
        os.makedirs(os.path.dirname(dummy_vert_path), exist_ok=True)
        if not os.path.exists(dummy_vert_path):
            with open(dummy_vert_path, 'w') as f:
                f.write("""
#version 330
in vec2 in_vert;
void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
""")
        if not os.path.exists(raymarching_frag_path):
            with open(raymarching_frag_path, 'w') as f:
                f.write("""
#version 330
uniform vec2 iResolution;
uniform float iTime;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution.xy;
    vec3 color = vec3(uv.x, uv.y, sin(iTime));
    fragColor = vec4(color, 1.0);
}
""")
        
        try:
            self.renderer = OffScreenRenderer(self.width, self.height, dummy_vert_path, raymarching_frag_path)
            if self.renderer.ctx is None:
                self.query_one("#video_display").update("[b]Error:[/b] Failed to initialize ModernGL context.")
                return
            self.set_interval(1.0 / self.fps, self.update_frame)
        except Exception as e:
            self.query_one("#video_display").update(f"[b]Error:[/b] Could not start renderer: {e}")

    def on_unmount(self) -> None:
        """Called when the app is unmounted."""
        if self.renderer:
            self.renderer.release()

    def _convert_image_to_text(self, img: Image.Image) -> str:
        """Converts a PIL Image to a string of colored text."""
        text_pixels = []
        width, height = img.size
        pixels = img.load()
        
        # We process two rows at a time for each character (upper and lower halves)
        # So, the effective height for iteration is height // 2
        for y in range(0, height - 1, 2):  # Iterate with a step of 2
            for x in range(width):
                # Get color for the upper pixel (background)
                ra, ga, ba = pixels[x, y]
                # Get color for the lower pixel (foreground)
                rb, gb, bb = pixels[x, y+1]
                
                # Use the half-block character with two colors using Textual's markup
                text_pixels.append(f"[rgb({rb},{gb},{bb}) on rgb({ra},{ga},{ba})]\u2584[/]")
            text_pixels.append("\n")
        return "".join(text_pixels)

    def update_frame(self) -> None:
        """Renders a new frame and updates the Static widget."""
        if not self.renderer:
            return

        current_time = time.time() - self.start_time
        frame_array = self.renderer.render_frame(current_time)

        if frame_array is not None:
            # 1. Convert float32 [0,1] array to uint8 [0,255] and then to a PIL Image
            img_data_uint8 = (frame_array[:, :, :3] * 255).astype(np.uint8)
            img = Image.fromarray(img_data_uint8, 'RGB')

            # 2. Convert the image to a colored text string
            text_frame = self._convert_image_to_text(img)

            # 3. Update the display widget
            video_display = self.query_one("#video_display", Static)
            video_display.update(text_frame)

if __name__ == "__main__":
    # To run with default settings:
    app = ShaderRenderApp()
    
    # Example of running with custom settings:
    # app = ShaderRenderApp(width=40, height=30, fps=5.0)
    
    app.run()
