# MooTube

A YouTube App for Mobile Linux.

### About
Browse and play media from YouTube without the need to sign-in. With the recent popularity of Linux Phones and the desire to stream media from YouTube, MooTube was born!

Supports both YouTube Video mode and YouTube Music mode with a convenient toggle switch!

### Features

- Search for Videos and Music
- Auto pagination to keep scrolling to load more results
- Toggle between Video and Music mode
- Download songs and videos to your offline library
- Playback control for media
- Filters for search

Video List | Playback | Music List
:-------------------------:|:-------------------------:|:-------------------------:
![Video List](https://github.com/ninebysix/MooTube/blob/master/docs/MooTube-VideosPage.png?raw=true) | ![Playback](https://github.com/ninebysix/MooTube/blob/master/docs/MooTube-VideoPlayback.png?raw=true) | ![Music List](https://github.com/ninebysix/MooTube/blob/master/docs/MooTube-MusicPage.png?raw=true)

### Instructions

0. (Prep) Install Dependencies:
  ```
   sudo apt install git python3 python3-pip libgtk-3-dev python3-requests python3-setuptools python3-gi python3-gi-cairo python3-opengl gir1.2-gtk-3.0 mpv libmpv-dev
  ```
1. Clone the MooTube repo:
  ```
   git clone --depth 1 https://github.com/ninebysix/MooTube.git ~/mootube
  ```
2. Change directory to MooTube repo:
  ```
   cd ~/mootube
  ```
3. Install the app:
  ```
   sudo python3 setup.py install
  ```

### TODO

- Custom playlists
- Additional media controls

### Donations Appreciated!

PayPal: https://www.paypal.me/jakeday42

Bitcoin: 1AH7ByeJBjMoAwsgi9oeNvVLmZHvGoQg68
