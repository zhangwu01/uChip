using SharpAvi;
using SharpAvi.Output;
using System.Diagnostics;
using System.Windows.Forms;
public static class Program {
    static Plotter plotterWindow;
    static Stopwatch timer = new Stopwatch();
    static Camera camera;
    static double last;
    static Camera.CameraImage lastImage;
    static CellDetector detector;
    const double CountWidth = 10.0f;
    static int width = 128;
    static int height = 128;
    static bool save = false;
    static int nFrames = 0;
    static Thread updateThread;

    [STAThread]
    static void Main(string[] args) {
        //if(args.Length == 3) {
        //    int.TryParse(args[0], out var w);
        //    int.TryParse(args[1], out var h);
        //    int.TryParse(args[2], out var save);
        //    width = w;
        //    height = h;
        //    Program.save = save > 0;
        //}
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        plotterWindow = new Plotter(CountWidth);
        plotterWindow.On1X += On1X;
        plotterWindow.On10X += On10X;
        plotterWindow.OnReset += ResetPlot;
        plotterWindow.OnRecord += StartRecording;
        plotterWindow.OnStopRecord += StopRecord;

        updateThread = new Thread(CameraLoop);
        updateThread.Start();

        System.Windows.Forms.Timer videoTimer = new System.Windows.Forms.Timer();
        videoTimer.Interval = 30;
        videoTimer.Tick += VideoUpdate;
        videoTimer.Start();

        System.Windows.Forms.Timer uiTimer = new System.Windows.Forms.Timer();
        uiTimer.Interval = 50;
        uiTimer.Tick += UIUpdate;
        uiTimer.Start();

        System.Windows.Forms.Timer cpsTimer = new System.Windows.Forms.Timer();
        cpsTimer.Interval = (int)CountWidth * 1000;
        cpsTimer.Tick += ComputeCPS;
        cpsTimer.Start();

        Application.Run(plotterWindow);
    }

    public static double TimeSinceStart {
        get {
            return timer.Elapsed.TotalMilliseconds / 1000;
        }
    }
    static void CameraLoop() {
        timer.Start();
        using (camera = new Camera()) {
            if(camera.camera == null) {
                return;
            }
            using (detector = new CellDetector(save)) {
                while (!plotterWindow.IsDisposed) {
                    Process();
                    nFrames++;
                }
            }
        }
    }

    static void Process() {
        plotterWindow.GetRect(out float roiX, out float roiY, out float roiW, out float roiH);
        lastImage = camera.Acquire(roiX, roiY, roiW, roiH);
        var motion = detector.ProcessImage(lastImage, plotterWindow.GetThreshold());
        plotterWindow.AddMotionDataPoint(motion);
        DoRecord(lastImage);
    }

    static void VideoUpdate(object sender, EventArgs args) {
        if (lastImage != null) {
            plotterWindow.DisplayImage(lastImage);
        }
    }

    static void UIUpdate(object sender, EventArgs args) {
        if(!updateThread.IsAlive) {
            plotterWindow.Close();
            return;
        }
        if(detector == null) {
            return;
        }
        var c = TimeSinceStart;
        var fps = nFrames / (c - last);
        nFrames = 0;
        last = c;
        int count = detector.detectedCells.Count;
        plotterWindow.UpdateLabels(fps, count);
        plotterWindow.RefreshPlots();
    }
    static void ComputeCPS(object sender, EventArgs args) {
        float cps = detector.CalculateCellsPerSecond();
        plotterWindow.AddCellsPerSecond(cps);
    }

    static void On1X()
    {
        camera.Set10X(false);
    }

    static void On10X()
    {
        camera.Set10X(true);
    }

    static void ResetPlot()
    {
        plotterWindow.ResetPlot();
        detector.Reset();
    }

    static bool _isRecording;
    static string targetFile;
    static void StartRecording()
    {
        if(_isRecording)
        {
            return;
        }
        var s = new SaveFileDialog();
        s.Filter = "Video|*.avi";
        s.Title = "Record Video";
        s.ShowDialog();
        if(s.FileName != "")
        {
            targetFile = s.FileName;
            _isRecording = true;
        }
    }

    static AviWriter writer;
    static IAviVideoStream stream;
    static double startTime;
    static void DoRecord(Camera.CameraImage image)
    {
        if(!_isRecording)
        {
            return;
        }

        if(writer == null)
        {
            startTime = TimeSinceStart;
            writer = new AviWriter(targetFile);
            writer.FramesPerSecond = 30;
            writer.EmitIndex1 = true;
            stream = writer.AddVideoStream();
            stream.Width = image.width;
            stream.Height = image.height;
            stream.Codec = CodecIds.Uncompressed;
            stream.BitsPerPixel = BitsPerPixel.Bpp24;
        }
        stream.WriteFrame(true, image.image, 0, image.image.Length);
    }

    static void StopRecord()
    {
        if (!_isRecording)
        {
            return;
        }

        writer.Close();
        writer = null;
        stream = null;
        _isRecording = false;
    }
}