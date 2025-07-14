using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using static Camera;

public class CellDetector : IDisposable
{
    private StreamWriter file;

    public struct Cell {
        public double detectionTime;
    }
    public List<Cell> detectedCells;
    public double lastCellsPerSecondTime;
    private bool save;
    public CellDetector(bool save) {
        lastCellsPerSecondTime = Program.TimeSinceStart;
        detectedCells = new List<Cell>();
        this.save = save;
        if (save) {
            file = new StreamWriter("CellDetections_" + DateTime.Now.ToString("yyyy-MM-dd-HH-mm-ss") + ".csv");
            file.WriteLine("Time (sec), Cells Detected");
        }
    }

    private bool motionDetected;
    private byte[] lastImage;
    private int[] difference;

    public class MotionData {
        public float motionAmount;
        public bool cellWasDetected;
        public double time;
    }
    public MotionData ProcessImage(CameraImage image, float threshold) {
        var data = new MotionData();
        if (lastImage == null || lastImage.Length != image.roiImage.Length) {
            lastImage = image.roiImage;
            difference = new int[lastImage.Length];
            return data;
        }
        Difference(image.roiImage, lastImage);
        data.motionAmount = difference.Length == 0 ? 0 : (float)difference.Average(x => (int)x);
        data.time = Program.TimeSinceStart;
        if(data.motionAmount < threshold && motionDetected) {
            var c = new Cell();
            c.detectionTime = data.time;
            lock (detectedCells) {
                detectedCells.Add(c);
            }
            data.cellWasDetected = true;
        }
        motionDetected = data.motionAmount > threshold;
        lastImage = image.roiImage;
        return data;
    }

    private void Difference(byte[] a, byte[] b) {
        for(int i = 0; i < a.Length; i++) {
            int an = a[i];
            int bn = b[i];
            difference[i] = Math.Abs(an - bn);
        }
    }

    public void Reset()
    {
        detectedCells.Clear();
    }

    public static float ComputeMax(in CameraImage data) {
        return 0;
    }

    public float CalculateCellsPerSecond() {
        var t = Program.TimeSinceStart;
        var n = 0;
        lock (detectedCells) {
            n = detectedCells.Count(x => x.detectionTime >= lastCellsPerSecondTime && x.detectionTime <= t);
        }
        var cps = n/(t - lastCellsPerSecondTime);
        lastCellsPerSecondTime = t;
        if (save) {
            file.WriteLine(t.ToString() + ", " + cps);
        }
        return (float)cps;
    }

    public void Dispose() {
        if (save) {
            file.Dispose();
        }
    }
}
