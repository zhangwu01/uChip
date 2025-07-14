using Basler.Pylon;
using System.Drawing.Imaging;

public class Camera : IDisposable {
    public struct CameraSettings {

    }


    public Basler.Pylon.Camera camera;

    public Camera() {
        camera = new Basler.Pylon.Camera();

        // Open the connection to the camera device.
        camera.Open();
        // Print the model name of the camera.
        Console.WriteLine("Using camera {0}.", camera.CameraInfo[CameraInfoKey.ModelName]);
    }

    public void Dispose() {
        if (camera != null) {
            camera.StreamGrabber.Stop();
            camera.Parameters[PLCamera.Width].SetToMaximum();
            camera.Parameters[PLCamera.Height].SetToMaximum();
            camera.Parameters[PLCamera.AcquisitionMode].SetValue(PLCamera.AcquisitionMode.Continuous);
            camera.Parameters[PLCamera.TriggerMode].SetValue(PLCamera.TriggerMode.Off);
            camera.Dispose();
        }
    }

    

    public static void Display(CameraImage data, int f = 0) {
        var d = data.image;
        if (data.roiImage != null) {
            d = new byte[d.Length];
            Array.Copy(data.image, d, d.Length);
            DrawBox(d, data.roiX1, data.roiX2, data.roiY1, data.roiY2, data.width, data.height, 0xFF);
        }
    }

    public static void Display(byte[] data, int width, int height, int f = 0) {
        ImageWindow.DisplayImage(f, data, PixelType.Mono8, width, height, 0, ImageOrientation.TopDown);
    }

    private static void DrawBox(byte[] data, int x1, int x2, int y1, int y2, int w, int h, byte boxColor) {
        for (int x = x1; x <= x2; x++) {
            data[y1 * w + x] = boxColor;
            data[y2 * w + x] = boxColor;
        }
        for (int y = y1; y <= y2; y++) {
            data[y * w + x1] = boxColor;
            data[y * w + x2] = boxColor;
        }
    }


    public CameraImage Acquire(float X = 0, float Y = 0, float W = 1, float H = 1) {
        var image = new CameraImage();
        lock (camera)
        {
            camera.ExecuteSoftwareTrigger();
            camera.WaitForFrameTriggerReady(5000, TimeoutHandling.ThrowException);
            IGrabResult grabResult = camera.StreamGrabber.RetrieveResult(5000, TimeoutHandling.ThrowException);
            using (grabResult)
            {
                // Image grabbed successfully?
                if (grabResult.GrabSucceeded)
                {
                    var data = grabResult.PixelData as byte[];
                    image.width = grabResult.Width;
                    image.height = grabResult.Height;
                    image.format = PixelFormat.Format16bppGrayScale
                    ComputeROI(ref image, X, Y, W, H);
                }
                else
                {
                    Console.WriteLine("Grab Error: {0} {1}", grabResult.ErrorCode, grabResult.ErrorDescription);
                }
            }
        }
        return image;
    }

    protected static void ComputeROI(ref CameraImage data, float X, float Y, float W, float H) {
        data.roiX1 = (int)((data.width - 1) * X);
        data.roiY1 = (int)((data.height - 1) * Y);
        int w = (int)(data.width * W);
        int h = (int)(data.height * H);
        data.roiX2 = Math.Min(data.width - 1, data.roiX1 + w);
        data.roiY2 = Math.Min(data.height - 1, data.roiY1 + h);

        w = 1+data.roiX2 - data.roiX1; 
        h = 1+data.roiY2 - data.roiY1;
        data.roiImage = new byte[w * h];
        for (int x = 0; x < w; x++) {
            for (int y = 0; y < h; y++) {
                int xd = x + data.roiX1;
                int yd = y + data.roiY1;
                data.roiImage[y * w + x] = data.image[yd * data.width + xd];
            }
        }
    }

    public void Set10X(bool enable)
    {   
        if(camera == null)
        {
            return;
        }
        lock (camera)
        {
            if (camera.StreamGrabber.IsGrabbing)
            {
                camera.StreamGrabber.Stop();
            }
            if (enable)
            {
                camera.Parameters[PLCamera.Width].SetValue(128);
                camera.Parameters[PLCamera.Height].SetValue(128);
            }
            else
            {
                camera.Parameters[PLCamera.Width].SetValue(640);
                camera.Parameters[PLCamera.Height].SetValue(240);
            }
            camera.StreamGrabber.Start();
        }
    }

    public void DisplayImage(Camera.CameraImage image) {
        if (bitmap == null || bitmap.Width != image.width || bitmap.Height != bitmap.Height || bitmap.PixelFormat != image.format) {
            if (bitmap != null) {
                bitmap.Dispose();
            }
            bitmap = new Bitmap(image.width, image.height, image.format);
            display.Image = bitmap;
        }

        // Lock the bitmap's bits.  
        System.Drawing.Rectangle rect = new System.Drawing.Rectangle(0, 0, bitmap.Width, bitmap.Height);
        BitmapData bmpData =
        bitmap.LockBits(rect, ImageLockMode.WriteOnly,
            bitmap.PixelFormat);

        // Get the address of the first line.
        IntPtr ptr = bmpData.Scan0;

        // Copy the RGB values back to the bitmap
        System.Runtime.InteropServices.Marshal.Copy(image.image, 0, ptr, image.image.Length);

        // Unlock the bits.
        bitmap.UnlockBits(bmpData);

        display.r = new System.Drawing.Rectangle((int)(((float)image.roiX1) / image.width * display.Width),
                                                 (int)(((float)image.roiY1) / image.height * display.Height),
                                                 (int)(((float)image.roiWidth) / image.width * display.Width),
                                                 (int)(((float)image.roiHeight) / image.height * display.Height));
        display.Refresh();
    }
}