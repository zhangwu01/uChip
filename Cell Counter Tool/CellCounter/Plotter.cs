using ScottPlot.Plottables;
using ScottPlot.WinForms;
using System.Collections.Generic;
using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using System.Diagnostics;
using System.Drawing.Imaging;

public partial class Plotter : Form
{

    FormsPlot motionPlot;
    FormsPlot cellCountPlot;
    Bitmap bitmap;

    readonly List<ScottPlot.Coordinates> motionPointsA = new List<ScottPlot.Coordinates>();
    readonly List<ScottPlot.Coordinates> motionPointsB = new List<ScottPlot.Coordinates>();
    readonly List<ScottPlot.Coordinates> detectedPointsA = new List<ScottPlot.Coordinates>();
    readonly List<ScottPlot.Coordinates> detectedPointsB = new List<ScottPlot.Coordinates>();
    bool isACurrent;

    readonly List<float> cellsPerSecond = new List<float>();
    readonly List<float> cellsPerSecondLogTimes = new List<float>();
    readonly VerticalLine timeMarkerLine;
    readonly HorizontalLine thresholdLine;
    double motionDisplayWidth;
    double motionLeftTime;
    double motionRightTime;
    public Plotter(double motionDisplayWidth)
    {
        this.motionDisplayWidth = motionDisplayWidth;
        InitializeComponent();
        motionPlot = new FormsPlot() { Dock = DockStyle.Fill };
        cellCountPlot = new FormsPlot { Dock = DockStyle.Fill };
        motionPlotPanel.Controls.Add(motionPlot);
        cellCountPlotPanel.Controls.Add(cellCountPlot);

        timeMarkerLine = motionPlot.Plot.Add.VerticalLine(0, 2, color: new ScottPlot.Color(100, 0, 0));
        thresholdLine = motionPlot.Plot.Add.HorizontalLine(0, 2, color: new ScottPlot.Color(0, 100, 100));

        cellCountPlot.Plot.Add.ScatterLine(cellsPerSecondLogTimes, cellsPerSecond);
        cellCountPlot.Plot.XLabel("Time (s)");
        cellCountPlot.Plot.YLabel("Cells/second");

        motionPlot.Plot.Add.ScatterLine(motionPointsA, color: new ScottPlot.Color(0, 0, 0));
        motionPlot.Plot.Add.ScatterPoints(detectedPointsA, color: new ScottPlot.Color(0, 255, 0));

        motionPlot.Plot.Add.ScatterLine(motionPointsB, color: new ScottPlot.Color(0, 0, 0));
        motionPlot.Plot.Add.ScatterPoints(detectedPointsB, color: new ScottPlot.Color(0, 255, 0));
        motionPlot.Plot.XLabel("Time (s)");
        motionPlot.Plot.YLabel("Motion");
        motionPlot.Plot.Axes.SetLimitsX(0, motionDisplayWidth);
    }

    public void UpdateLabels(double fps, int nDetected)
    {
        this.fpsLabel.Text = "FPS: " + fps.ToString();
        totalDetectedLabel.Text = "Detected " + nDetected;
        x = roiXBar.Value / 100.0f;
        y = roiYBar.Value / 100.0f;
        w = roiWBar.Value / 100.0f;
        h = roiHBar.Value / 100.0f;
    }

    public void AddCellsPerSecond(float cps)
    {
        cellsPerSecond.Add(cps);
        cellsPerSecondLogTimes.Add((float)(Program.TimeSinceStart - resetTime));
    }

    public float GetThreshold()
    {
        return (float)cutoff.Value;
    }

    public void DisplayImage(Camera.CameraImage image)
    {
        if (bitmap == null || bitmap.Width != image.width || bitmap.Height != bitmap.Height || bitmap.PixelFormat != image.format)
        {
            if (bitmap != null)
            {
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

    private float x, y, w, h;
    public void GetRect(out float x, out float y, out float w, out float h)
    {
        x = this.x;
        y = this.y;
        w = this.w;
        h = this.h;
    }

    public void AddMotionDataPoint(CellDetector.MotionData motionData)
    {
        lock (motionPointsA)
        {
            double t = motionData.time - motionLeftTime;
            var motionPoints = isACurrent ? motionPointsA : motionPointsB;
            var detectedPoints = isACurrent ? detectedPointsA : detectedPointsB;
            motionPoints.Add(new ScottPlot.Coordinates(t, motionData.motionAmount));
            if (motionData.cellWasDetected)
            {
                detectedPoints.Add(new ScottPlot.Coordinates(t, -5));
            }
        }
    }

    public double resetTime = 0;
    public void ResetPlot()
    {
        resetTime = Program.TimeSinceStart;
        cellsPerSecondLogTimes.Clear();
        cellsPerSecond.Clear();
        cellCountPlot.Refresh();
    }

    public void RefreshPlots()
    {
        var t = Program.TimeSinceStart;
        if (t > motionRightTime)
        {
            motionLeftTime = motionRightTime;
            motionRightTime = motionLeftTime + motionDisplayWidth;
            isACurrent = !isACurrent;
            var motionPoints = isACurrent ? motionPointsA : motionPointsB;
            var detectedPoints = isACurrent ? detectedPointsA : detectedPointsB;
            motionPoints.Clear();
            detectedPoints.Clear();
        }
        t = t - motionLeftTime;

        thresholdLine.Position = GetThreshold();
        timeMarkerLine.Position = t;

        // Now need to purge the old one
        var oldMotionPoints = isACurrent ? motionPointsB : motionPointsA;
        var oldDetectedPoints = isACurrent ? detectedPointsB : detectedPointsA;

        double cutoff = t + motionDisplayWidth * 0.05;
        for (int i = oldMotionPoints.Count - 1; i >= 0; i--)
        {
            if (oldMotionPoints[i].X <= cutoff)
            {
                oldMotionPoints.RemoveAt(i);
            }
        }
        for (int i = oldDetectedPoints.Count - 1; i >= 0; i--)
        {
            if (oldDetectedPoints[i].X <= cutoff)
            {
                oldDetectedPoints.RemoveAt(i);
            }
        }

        double maxMotion = 0;
        lock (motionPointsA)
        {
            var pts = motionPointsA.Concat(motionPointsB).Select(x => x.Y).DefaultIfEmpty();
            maxMotion = Math.Max(pts.Max(), thresholdLine.Position);
            motionPlot.Plot.Axes.SetLimitsY(-10, maxMotion * 1.1);
            motionPlot.Refresh();
        }

        float timeMax = cellsPerSecondLogTimes.Count == 0 ? 0 : cellsPerSecondLogTimes.Max();
        float cpsMax = cellsPerSecond.Count == 0 ? 0 : cellsPerSecond.Max();
        cellCountPlot.Plot.Axes.SetLimits(0, timeMax * 1.1f, 0, cpsMax * 1.1f);
        cellCountPlot.Refresh();
    }

    private void InitializeComponent()
    {
        label6 = new Label();
        label4 = new Label();
        label3 = new Label();
        label2 = new Label();
        roiHBar = new TrackBar();
        roiWBar = new TrackBar();
        roiYBar = new TrackBar();
        roiXBar = new TrackBar();
        fpsLabel = new Label();
        label1 = new Label();
        cutoff = new NumericUpDown();
        motionPlotPanel = new Panel();
        cellCountPlotPanel = new Panel();
        totalDetectedLabel = new Label();
        display = new PylonCamera.PictureBoxNN();
        button1 = new Button();
        button2 = new Button();
        button3 = new Button();
        tabControl1 = new TabControl();
        tabPage1 = new TabPage();
        button4 = new Button();
        saveFileDialog1 = new SaveFileDialog();
        this.button5 = new Button();
        ((System.ComponentModel.ISupportInitialize)roiHBar).BeginInit();
        ((System.ComponentModel.ISupportInitialize)roiWBar).BeginInit();
        ((System.ComponentModel.ISupportInitialize)roiYBar).BeginInit();
        ((System.ComponentModel.ISupportInitialize)roiXBar).BeginInit();
        ((System.ComponentModel.ISupportInitialize)cutoff).BeginInit();
        ((System.ComponentModel.ISupportInitialize)display).BeginInit();
        tabControl1.SuspendLayout();
        tabPage1.SuspendLayout();
        SuspendLayout();
        // 
        // label6
        // 
        label6.AutoSize = true;
        label6.Location = new Point(6, 426);
        label6.Name = "label6";
        label6.Size = new Size(36, 15);
        label6.TabIndex = 10;
        label6.Text = "ROI Y";
        // 
        // label4
        // 
        label4.AutoSize = true;
        label4.Location = new Point(6, 488);
        label4.Name = "label4";
        label4.Size = new Size(38, 15);
        label4.TabIndex = 8;
        label4.Text = "ROI H";
        // 
        // label3
        // 
        label3.AutoSize = true;
        label3.Location = new Point(6, 457);
        label3.Name = "label3";
        label3.Size = new Size(40, 15);
        label3.TabIndex = 7;
        label3.Text = "ROI W";
        // 
        // label2
        // 
        label2.AutoSize = true;
        label2.Location = new Point(6, 395);
        label2.Name = "label2";
        label2.Size = new Size(36, 15);
        label2.TabIndex = 6;
        label2.Text = "ROI X";
        label2.Click += label2_Click;
        // 
        // roiHBar
        // 
        roiHBar.AutoSize = false;
        roiHBar.BackColor = SystemColors.Control;
        roiHBar.Location = new Point(95, 490);
        roiHBar.Maximum = 100;
        roiHBar.Name = "roiHBar";
        roiHBar.Size = new Size(212, 20);
        roiHBar.TabIndex = 4;
        roiHBar.TickStyle = TickStyle.None;
        roiHBar.Value = 100;
        // 
        // roiWBar
        // 
        roiWBar.AutoSize = false;
        roiWBar.BackColor = SystemColors.Control;
        roiWBar.Location = new Point(95, 457);
        roiWBar.Maximum = 100;
        roiWBar.Name = "roiWBar";
        roiWBar.Size = new Size(212, 20);
        roiWBar.TabIndex = 3;
        roiWBar.TickStyle = TickStyle.None;
        roiWBar.Value = 100;
        // 
        // roiYBar
        // 
        roiYBar.AutoSize = false;
        roiYBar.BackColor = SystemColors.Control;
        roiYBar.Location = new Point(95, 424);
        roiYBar.Maximum = 100;
        roiYBar.Name = "roiYBar";
        roiYBar.Size = new Size(212, 20);
        roiYBar.TabIndex = 2;
        roiYBar.TickStyle = TickStyle.None;
        // 
        // roiXBar
        // 
        roiXBar.AutoSize = false;
        roiXBar.BackColor = SystemColors.Control;
        roiXBar.Location = new Point(95, 391);
        roiXBar.Maximum = 100;
        roiXBar.Name = "roiXBar";
        roiXBar.Size = new Size(212, 20);
        roiXBar.TabIndex = 1;
        roiXBar.TickStyle = TickStyle.None;
        // 
        // fpsLabel
        // 
        fpsLabel.AutoSize = true;
        fpsLabel.Location = new Point(24, 26);
        fpsLabel.Name = "fpsLabel";
        fpsLabel.Size = new Size(32, 15);
        fpsLabel.TabIndex = 13;
        fpsLabel.Text = "FPS: ";
        // 
        // label1
        // 
        label1.AutoSize = true;
        label1.Location = new Point(6, 364);
        label1.Name = "label1";
        label1.Size = new Size(83, 15);
        label1.TabIndex = 11;
        label1.Text = "Motion Cutoff";
        // 
        // cutoff
        // 
        cutoff.DecimalPlaces = 3;
        cutoff.Location = new Point(95, 362);
        cutoff.Maximum = new decimal(new int[] { 10000000, 0, 0, 0 });
        cutoff.Name = "cutoff";
        cutoff.Size = new Size(212, 23);
        cutoff.TabIndex = 14;
        // 
        // motionPlotPanel
        // 
        motionPlotPanel.Location = new Point(6, 10);
        motionPlotPanel.Name = "motionPlotPanel";
        motionPlotPanel.Size = new Size(312, 341);
        motionPlotPanel.TabIndex = 2;
        // 
        // cellCountPlotPanel
        // 
        cellCountPlotPanel.Location = new Point(324, 10);
        cellCountPlotPanel.Name = "cellCountPlotPanel";
        cellCountPlotPanel.Size = new Size(325, 341);
        cellCountPlotPanel.TabIndex = 3;
        // 
        // totalDetectedLabel
        // 
        totalDetectedLabel.AutoSize = true;
        totalDetectedLabel.Location = new Point(324, 408);
        totalDetectedLabel.Name = "totalDetectedLabel";
        totalDetectedLabel.Size = new Size(110, 15);
        totalDetectedLabel.TabIndex = 15;
        totalDetectedLabel.Text = "Total Cells Detected";
        // 
        // display
        // 
        display.Location = new Point(24, 49);
        display.Name = "display";
        display.Size = new Size(439, 409);
        display.SizeMode = PictureBoxSizeMode.CenterImage;
        display.TabIndex = 16;
        display.TabStop = false;
        // 
        // button1
        // 
        button1.Location = new Point(24, 474);
        button1.Name = "button1";
        button1.Size = new Size(207, 29);
        button1.TabIndex = 17;
        button1.Text = "1X";
        button1.UseVisualStyleBackColor = true;
        button1.Click += button1_Click;
        // 
        // button2
        // 
        button2.Location = new Point(237, 474);
        button2.Name = "button2";
        button2.Size = new Size(226, 29);
        button2.TabIndex = 18;
        button2.Text = "10X";
        button2.UseVisualStyleBackColor = true;
        button2.Click += button2_Click;
        // 
        // button3
        // 
        button3.Location = new Point(324, 362);
        button3.Name = "button3";
        button3.Size = new Size(153, 29);
        button3.TabIndex = 19;
        button3.Text = "Restart Tracing";
        button3.UseVisualStyleBackColor = true;
        button3.Click += button3_Click;
        // 
        // tabControl1
        // 
        tabControl1.Controls.Add(tabPage1);
        tabControl1.Location = new Point(469, 26);
        tabControl1.Name = "tabControl1";
        tabControl1.SelectedIndex = 0;
        tabControl1.Size = new Size(678, 558);
        tabControl1.TabIndex = 20;
        // 
        // tabPage1
        // 
        tabPage1.Controls.Add(label6);
        tabPage1.Controls.Add(cutoff);
        tabPage1.Controls.Add(label2);
        tabPage1.Controls.Add(label1);
        tabPage1.Controls.Add(label4);
        tabPage1.Controls.Add(totalDetectedLabel);
        tabPage1.Controls.Add(roiXBar);
        tabPage1.Controls.Add(motionPlotPanel);
        tabPage1.Controls.Add(label3);
        tabPage1.Controls.Add(roiYBar);
        tabPage1.Controls.Add(button3);
        tabPage1.Controls.Add(roiWBar);
        tabPage1.Controls.Add(cellCountPlotPanel);
        tabPage1.Controls.Add(roiHBar);
        tabPage1.Location = new Point(4, 24);
        tabPage1.Name = "tabPage1";
        tabPage1.Padding = new Padding(3);
        tabPage1.Size = new Size(670, 530);
        tabPage1.TabIndex = 0;
        tabPage1.Text = "Cell Counter";
        tabPage1.UseVisualStyleBackColor = true;
        // 
        // button4
        // 
        button4.Location = new Point(24, 526);
        button4.Name = "button4";
        button4.Size = new Size(439, 29);
        button4.TabIndex = 21;
        button4.Text = "Start Recording";
        button4.UseVisualStyleBackColor = true;
        button4.Click += button4_Click;
        // 
        // button5
        // 
        this.button5.Location = new Point(24, 561);
        this.button5.Name = "button5";
        this.button5.Size = new Size(439, 29);
        this.button5.TabIndex = 22;
        this.button5.Text = "Stop Recording";
        this.button5.UseVisualStyleBackColor = true;
        this.button5.Click += this.button5_Click;
        // 
        // Plotter
        // 
        AutoScaleMode = AutoScaleMode.None;
        ClientSize = new Size(1165, 600);
        Controls.Add(this.button5);
        Controls.Add(button4);
        Controls.Add(tabControl1);
        Controls.Add(button2);
        Controls.Add(button1);
        Controls.Add(display);
        Controls.Add(fpsLabel);
        Name = "Plotter";
        FormClosed += Plotter_FormClosed;
        ((System.ComponentModel.ISupportInitialize)roiHBar).EndInit();
        ((System.ComponentModel.ISupportInitialize)roiWBar).EndInit();
        ((System.ComponentModel.ISupportInitialize)roiYBar).EndInit();
        ((System.ComponentModel.ISupportInitialize)roiXBar).EndInit();
        ((System.ComponentModel.ISupportInitialize)cutoff).EndInit();
        ((System.ComponentModel.ISupportInitialize)display).EndInit();
        tabControl1.ResumeLayout(false);
        tabPage1.ResumeLayout(false);
        tabPage1.PerformLayout();
        ResumeLayout(false);
        PerformLayout();
    }

    private void Plotter_FormClosed(object sender, FormClosedEventArgs e)
    {
        if (bitmap != null)
        {
            bitmap.Dispose();
        }
    }

    public delegate void clickDelegate();
    public clickDelegate On1X;
    public clickDelegate On10X;
    public clickDelegate OnReset;
    public clickDelegate OnRecord;
    public clickDelegate OnStopRecord;
    private void button1_Click(object sender, EventArgs e)
    {
        On1X.Invoke();
    }

    private void button2_Click(object sender, EventArgs e)
    {
        On10X.Invoke();
    }

    private void button3_Click(object sender, EventArgs e)
    {
        OnReset.Invoke();
    }

    private void label2_Click(object sender, EventArgs e)
    {

    }

    private void button4_Click(object sender, EventArgs e)
    {
        OnRecord.Invoke();
    }

    private void button5_Click(object sender, EventArgs e)
    {
        OnStopRecord.Invoke();
    }
}