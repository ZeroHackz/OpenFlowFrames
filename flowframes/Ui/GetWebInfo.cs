using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace Flowframes.Ui
{
    class GetWebInfo
    {
        public static async Task LoadNews (Label newsLabel)
        {
            try
            {
                string url = $"https://raw.githubusercontent.com/ZeroHackz/OpenFlowFrames/main/changelog.txt";
                var client = new WebClient();
                var str = await client.DownloadStringTaskAsync(new Uri(url));
                newsLabel.Text = str;
            }
            catch(Exception e)
            {
                Logger.Log($"Failed to load news: {e.Message}", true);
            }
        }
    }
}
