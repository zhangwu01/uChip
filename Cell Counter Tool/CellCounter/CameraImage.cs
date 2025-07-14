using Basler.Pylon;
using System.Drawing.Imaging;

public class CameraImage {
    public byte[] image;
    public byte[] roiImage;
    public int width;
    public int height;
    public int roiWidth { get { return 1 + roiX2 - roiX1; } }
    public int roiHeight { get { return 1 + roiY2 - roiY1; } }
    public int roiX1;
    public int roiY1;
    public int roiX2;
    public int roiY2;
    public PixelFormat format;
}