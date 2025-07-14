using PylonCamera;

partial class Plotter {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing) {
            if (disposing && (components != null)) {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        private System.Windows.Forms.Splitter splitter1;
        private System.Windows.Forms.TrackBar roiHBar;
        private System.Windows.Forms.TrackBar roiWBar;
        private System.Windows.Forms.TrackBar roiYBar;
        private System.Windows.Forms.TrackBar roiXBar;
        private System.Windows.Forms.Label label6;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label fpsLabel;
    private System.Windows.Forms.NumericUpDown cutoff;
    private System.Windows.Forms.Panel motionPlotPanel;
    private System.Windows.Forms.Panel cellCountPlotPanel;
    private System.Windows.Forms.Label totalDetectedLabel;
    private PictureBoxNN display;
    private Button button1;
    private Button button2;
    private Button button3;
    private TabControl tabControl1;
    private TabPage tabPage1;
    private Button button4;
    private SaveFileDialog saveFileDialog1;
    private Button button5;
}