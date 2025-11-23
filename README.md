# SeedUp - Smart Torrent Management V1.0

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/codercyco/SeedUp/blob/main/SeedUp.ipynb)

<div align="center">

<br>
<a href="https://www.buymeacoffee.com/codercyco" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" width="300">
</a>

<br>

### 🌐 **Connect & Stay Updated**

  <div style="display: flex; justify-content: center; align-items: center; gap: 10px; flex-wrap: wrap;">
    <a href="https://www.linkedin.com/in/isharadeshapriya/" target="_blank">
      <img src="https://img.shields.io/badge/Follow-LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="Follow on LinkedIn" height="30">
    </a>
    <a href="https://www.linkedin.com/newsletters/7355638830797901825/" target="_blank">
      <img src="https://img.shields.io/badge/Subscribe-Newsletter-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="Subscribe to Newsletter" height="30">
    </a>
    <a href="https://www.youtube.com/@0xbashbyte" target="_blank">
      <img src="https://img.shields.io/badge/Subscribe-YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Subscribe on YouTube" height="30">
    </a>
    <a href="https://whatsapp.com/channel/0029Vb6SY8iBPzjWxxQCYN2R" target="_blank">
      <img src="https://img.shields.io/badge/Join-Community-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" alt="Join WhatsApp Community" height="30">
    </a>
  </div>

</div>

##  Overview

SeedUp is a powerful Python-based tool that seamlessly combines torrent downloading with Google Drive uploading capabilities. Designed for both standalone applications and Google Colab environments, SeedUp allows you to manage large downloads efficiently without consuming your local storage resources.

Perfect for users who need to download large files through torrents and automatically store them in cloud storage, especially useful in resource-constrained environments like Google Colab's free tier.

##  Features

-  **High-speed torrent downloading** using libtorrent
-  **Automatic Google Drive upload** with seamless authentication
- ⏸ **Resume capability** for interrupted downloads
-  **Real-time progress tracking** with visual progress bars
-  **Smart duplicate detection** - skip already uploaded files
-  **Flexible input support** - both magnet links and .torrent files
-  **Google Colab optimized** with automatic environment detection
-  **Secure authentication** handling for Google Drive API
-  **Organized uploads** with configurable destination folders
-  **Command-line interface** for advanced users

##  Installation

### For Google Colab (Recommended)
Simply open the [SeedUp Colab Notebook](https://colab.research.google.com/github/codercyco/SeedUp/blob/main/SeedUp.ipynb) and follow the step-by-step guide. No manual installation required!

### For Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/codercyco/SeedUp.git
   cd SeedUp
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install libtorrent:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install python3-libtorrent
   
   # macOS
   brew install libtorrent-rasterbar
   
   # Or via pip (may require compilation)
   pip install libtorrent
   ```
<br>

## Quick Start
### In Google Colab (Easiest)
1. Click here to Open [SeedUp Colab Notebook](https://colab.research.google.com/github/codercyco/SeedUp/blob/main/SeedUp.ipynb)
2. Follow the step-by-step cells
3. Authentication and setup is handled automatically

### Command Line Usage

#### Download torrent only:
```bash
python main.py download -t "magnet:?xt=urn:btih:..."
python main.py download -t movie.torrent
```

#### Download and upload to Google Drive:
```bash
python main.py download -t "magnet:?xt=urn:btih:..." --upload -f FOLDER_ID
```

#### Upload existing files to Google Drive:
```bash
python main.py upload -p /path/to/folder -f FOLDER_ID
```

#### Check download status:
```bash
python main.py status
```

#### Clear session:
```bash
python main.py clear
```

### Advanced Options

- `--no-resume`: Start fresh download (ignore previous session)
- `--no-skip`: Force re-upload even if files exist in Drive
- `-d PATH`: Custom download destination
- `-f FOLDER_ID`: Google Drive folder ID for uploads

##  Project Structure

```
SeedUp/
├── main.py                 # Main CLI entry point
├── torrent_downloader.py   # Torrent downloading logic
├── gdrive_uploader.py      # Google Drive upload functionality
├── config.py               # Configuration and constants
├── requirements.txt        # Python dependencies
├── SeedUp.ipynb           # Google Colab notebook
├── LICENSE                 # GPL v3 license
└── README.md              # This file
```

##  Configuration

### Google Drive Setup
1. **Get Folder ID:**
   - Open [Google Drive](https://drive.google.com)
   - Navigate to your target folder
   - Copy the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

2. **Authentication:**
   - In Colab: Automatic authentication via `google.colab.auth`
   - Local: Manual OAuth2 flow (credentials required)

### Environment Variables
Key configuration options in `config.py`:

```python
TORRENT_DOWNLOAD_PATH = "../SeedUp Downloads"  # Default download path
CHUNK_SIZE = 100 * 1024 * 1024                # 100MB upload chunks
MAX_RETRIES = 3                                # Upload retry attempts
LARGE_FILE_THRESHOLD = 1024 * 1024 * 1024      # 1GB threshold
```

##  Use Cases

### Perfect for:

- **Anyone**: Who needs cloud storage for torrent downloads

### Environments:
- ✅ **Google Colab** (Recommended - zero setup)
- ✅ **Local Linux/macOS** (With proper dependencies)
- ✅ **WSL on Windows** (Linux subsystem)
- ❌ **Native Windows** (libtorrent limitations)

##  Important Considerations

### Legal Compliance
- **Only download content you have legal rights to access**
- **Respect copyright and intellectual property laws**
- **Be aware of your local regulations regarding torrents**
- **This tool is for legitimate use cases only**

### Google Colab Limitations
- **Runtime Limit**: ~12 hours maximum session
- **Disk Space**: Limited to ~100GB temporary storage
- **Session Management**: May disconnect if idle
- **Network Speed**: Variable depending on Colab allocation

### Best Practices
1. **Monitor sessions** for long downloads
2. **Use resume capability** for interrupted downloads
3. **Clear downloads folder** after successful uploads
4. **Respect Drive storage quotas**
5. **Test with small files first**

##  Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request



##  License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

### What this means:
- ✅ **Commercial Use** - You can use this software commercially
- ✅ **Modification** - You can modify the source code
- ✅ **Distribution** - You can distribute the software
- ✅ **Private Use** - You can use it privately
- ✅ **Patent Grant** - Contributors provide an express grant of patent rights
- ⚠️ **Trademark Use** - You cannot use contributors' names, logos, or trademarks
- ⚠️ **Liability** - Software is provided "as is" without warranty

##  Acknowledgments

- **libtorrent** team for the excellent torrent library
- **Google** for Colab platform and Drive API
- **Python community** for amazing ecosystem
- **Open source contributors** who make projects like this possible

##  Links

- **[GitHub Repository](https://github.com/codercyco/SeedUp)**
- **[Report Issues](https://github.com/codercyco/SeedUp/issues)**
- **[Colab Notebook](https://colab.research.google.com/github/codercyco/SeedUp/blob/main/SeedUp.ipynb)**

---

<div align="center">

**Made with ❤️ for the BashByte community**

**Created by [Ishara Deshapriya](https://www.linkedin.com/in/isharadeshapriya/)**

**Licensed under Apache License 2.0**
</div>