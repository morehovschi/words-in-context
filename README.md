## *word-recon*: make input comprehensible

### tldr
This is a Python desktop app that serves as a language learning companion. It analyzes the given subtitle files in the `data` folder,
counts the words in all the files of the selected target language, and outputs a ranked list of the most common words. The user interface
shows the statistics for any chosen word, shows contextual examples (sentences), and can translate and play an audio of the sentence
to clarify pronunciation. The example and translation box can be saved as a flash card, and then all flash cards can be exported to one
or more Anki decks.

Quick demo: https://drive.google.com/file/d/1VhKB__TjuWnBvOfQPLN5KhR2Aka78A4G/view?usp=drive_link

### Setup
1. Clone this repository and `cd` into it
2. Create a Python environment `python3 -m venv env`
3. Activate the environment `source /env/bin/activate`
4. `pip install -r requirements.txt`

To run:
1. Activate the environment `source /env/bin/activate`
2. `python3 gui.py`

### Why?
According to linguists such as Stephen Krashen, language is acquired through comprehensible input.
Nice explanation: https://www.youtube.com/watch?v=NiTsduRreug&ab_channel=MarkRounds
That is, in order to learn a language, start by consuming interesting and comprehensible content (for example movies) in your target
language. But the difficulty in the beginning is that almost none of the input is comprehensible.

This app allows for studying subtitle files ahead of time, and memorize words and sentences that occur in the movie/episode. This
should make the content a bit more comprehensible and speed up (and make more enjoyable) the initial stages of language learning.

### Word classification
The metric used for classification is the TF-IDF metric, not raw frequency, as frequency tends to prioritize stop words (e.g. "a”,
“the”, “is”, “are”), which are common in any given text and not particularly interesting memorizable vocabulary. TF-IDF can be summarized
as "word frequency divided by number of documents word occurs in" - so it prioritizes words common in our target document, but uncommon
in others. Thus it shows words most likely to be relevant for memorizing ahead of watching a movie/episode.

In addition, word-recon offers name filtering, which is a best effort algorithm to filter out proper nouns (e.g. "Bob", "Alice",
"Greenland"), as they do not represent vocabulary in the target language.

### Export as Anki decks
The example and translation box are editable and can be saved as flash cards, where the front is the example word and sentence in the
target language and the back is the translated word and sentence. The saved flash cards can be exported as Anki decks, which upon opening
are saved into Anki under the given deck names. The Anki app provides a nice spaced repetition system and is available on multiple platforms
(mac, iOS, Windows, Android).

This app is unrelated to the Anki project, but it can act as a complement to it, providing a fast and convenient way to create language
learning flash cards.

### Supported languages
European languages supported by spaCy and Google Translate, as this app depends on their functionality for lemmatization, translation
and text-to-audio generation.

Catalan, Croatian, Danish, Dutch, English, Finnish, French, German, Greek, Italian, Lithuanian, Macedonian, Norwegian, Polish, Portuguese,
Romanian, Slovenian, Spanish, Swedish, Ukrainian.


