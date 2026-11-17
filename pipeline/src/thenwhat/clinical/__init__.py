"""A claim's clinical categories: the MeSH descriptors its approved trials and papers
give it, the tree they sit in, and the reader-friendly topics derived from them.
Behavior: openspec clinical-classification.

Nothing here is stored per claim. Categories are derived from stored registry and index
records each time they are read, so they are the same from either store.
"""
