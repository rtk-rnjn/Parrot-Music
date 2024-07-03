# Parrot Music Bot

## Music Bot Usage

### Join

**Description:**

- The bot joins the voice channel of the user.
- If the bot is already connected to a voice channel, it will move to the user's voice channel if the user has DJ permissions.

**Usage:** `!join`

---

### Move

**Description:**

- Moves the bot to the specified voice channel or to the user's current voice channel.
- If the bot is already playing in another channel, it will ask for confirmation to move.

**Usage:** `!move [channel]`

---

### Play

**Description:**

- Plays a song from YouTube or Spotify based on the given query.
- Adds the song to the queue if something is already playing.

**Usage:** `!play [song name or URL]`

---

### Search

**Description:**

- Searches for a song on YouTube or Spotify based on the given query.
- Displays a list of the top results for the user to choose from.
- User can select a song by typing the number of the song they want to play.

**Usage:** `!search [song name or URL]`

---

### Skip

**Description:**

- Skips the currently playing song and plays the next one in the queue.

**Usage:** `!skip`

---

### Pause/Resume

**Description:**

- Pauses or resumes the currently playing song.

**Usage:** `!pause` or `!resume`

---

### Disconnect

**Description:**

- Disconnects the bot from the voice channel.

**Usage:** `!disconnect`

---

### Volume

**Description:**

- Sets the volume of the player.
- Accepts values between 0 and 100.
- Supports relative volume changes with `+` and `-`.

**Usage:** `!volume [0-100]` or `!volume [+10]` or `!volume [-10]`

---

### Shuffle

**Description:**

- Shuffles the current queue.

**Usage:** `!shuffle`

---

### Now Playing

**Description:**

- Shows the currently playing song.

**Usage:** `!nowplaying` or `!np`

---

### Stop

**Description:**

- Stops the player and clears the queue.

**Usage:** `!stop`

---

### Queue

**Description:**

- Displays the current queue of songs.

**Usage:** `!queue`

---

### Clear

**Description:**

- Clears the current queue.
- Requires confirmation from the user.

**Usage:** `!clear`

---

### Lyrics

**Description:**

- Displays the lyrics of the currently playing song.

**Usage:** `!lyrics`

---

### Seek

**Description:**

- Seeks to a specific time in the current song.
- Supports relative seeking with `+` and `-`.

**Usage:** `!seek [seconds]` or `!seek [+10]` or `!seek [-10]`

---

### Example Usage

- `!play Despacito`
- `!search Imagine Dragons`
- `!volume 50`
- `!seek 60`
- `!shuffle`

Note: Ensure the user and the bot are in the same voice channel to use most commands.
