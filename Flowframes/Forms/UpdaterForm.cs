using Flowframes.Data;
using Flowframes.Os;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace Flowframes.Forms
{
    public partial class UpdaterForm : Form
    {
        Version installed;
        Version latestFree;

        public UpdaterForm()
        {
            AutoScaleMode = AutoScaleMode.None;
            InitializeComponent();
        }

        private async void UpdaterForm_Load(object sender, EventArgs e)
        {
            installed = Updater.GetInstalledVer();
            latestFree = Updater.GetLatestVer(false);

            installedLabel.Text = installed.ToString();
            await Task.Delay(100);
            latestLabel.Text = latestFree.ToString();

            if (Updater.CompareVersions(installed, latestFree) == Updater.VersionCompareResult.Equal)
            {
                statusLabel.Text = "Latest Version Is Installed.";
                return;
            }

            statusLabel.Text = Updater.CompareVersions(installed, latestFree) == Updater.VersionCompareResult.Newer
                ? "Update Available."
                : "You Are Running A Newer Version Than The Latest Release.";
        }

        float lastProg = -1f;
        public void SetProgLabel (float prog, string str)
        {
            if (prog == lastProg) return;
            lastProg = prog;
            downloadingLabel.Text = str;
        }

        private void updateFreeBtn_Click(object sender, EventArgs e)
        {
            string link = Updater.GetLatestVerLink(false);
            if (!string.IsNullOrWhiteSpace(link))
                Process.Start(link);
        }
    }
}
