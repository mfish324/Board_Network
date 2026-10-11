"""
Name standardization module for director names.

Handles normalization of director names to enable matching across
different filings and companies.
"""

import re
from typing import Optional

# Comprehensive nickname mapping
NICKNAME_MAP = {
    # Male names
    'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'robbie': 'robert',
    'bill': 'william', 'billy': 'william', 'will': 'william', 'willie': 'william',
    'jim': 'james', 'jimmy': 'james', 'jamie': 'james',
    'mike': 'michael', 'mick': 'michael', 'mickey': 'michael', 'mikey': 'michael',
    'dick': 'richard', 'rick': 'richard', 'ricky': 'richard', 'rich': 'richard',
    'tom': 'thomas', 'tommy': 'thomas',
    'joe': 'joseph', 'joey': 'joseph',
    'jack': 'john', 'johnny': 'john', 'jon': 'john',
    'dan': 'daniel', 'danny': 'daniel',
    'dave': 'david', 'davey': 'david',
    'steve': 'steven', 'stevie': 'steven',
    'chris': 'christopher',
    'tony': 'anthony',
    'ted': 'theodore', 'teddy': 'theodore',
    'ed': 'edward', 'eddie': 'edward', 'eddy': 'edward',
    'al': 'albert', 'albie': 'albert',
    'alex': 'alexander',
    'andy': 'andrew', 'drew': 'andrew',
    'ben': 'benjamin', 'benny': 'benjamin', 'benji': 'benjamin',
    'charlie': 'charles', 'chuck': 'charles', 'chas': 'charles',
    'doug': 'douglas',
    'fred': 'frederick', 'freddy': 'frederick', 'freddie': 'frederick',
    'greg': 'gregory',
    'jeff': 'jeffrey', 'geoff': 'geoffrey',
    'ken': 'kenneth', 'kenny': 'kenneth',
    'larry': 'lawrence', 'lance': 'lawrence',
    'matt': 'matthew', 'matty': 'matthew',
    'nick': 'nicholas', 'nicky': 'nicholas',
    'pat': 'patrick', 'paddy': 'patrick',
    'pete': 'peter',
    'phil': 'phillip', 'philip': 'phillip',
    'ron': 'ronald', 'ronnie': 'ronald',
    'sam': 'samuel', 'sammy': 'samuel',
    'tim': 'timothy', 'timmy': 'timothy',
    'gene': 'eugene',
    'gus': 'augustus',
    'hank': 'henry',
    'josh': 'joshua',
    'lenny': 'leonard',
    'max': 'maxwell',
    'nate': 'nathan', 'nathaniel': 'nathan',
    'randy': 'randall', 'randolph': 'randall',
    'ray': 'raymond',
    'terry': 'terrence',
    'vinny': 'vincent', 'vince': 'vincent',
    'zack': 'zachary', 'zach': 'zachary',

    # Female names
    'liz': 'elizabeth', 'lizzie': 'elizabeth', 'beth': 'elizabeth',
    'betty': 'elizabeth', 'betsy': 'elizabeth', 'libby': 'elizabeth',
    'kate': 'katherine', 'katie': 'katherine', 'kathy': 'katherine',
    'cathy': 'catherine', 'cathie': 'catherine', 'cat': 'catherine',
    'jenny': 'jennifer', 'jen': 'jennifer', 'jenn': 'jennifer',
    'sue': 'susan', 'susie': 'susan', 'suzy': 'susan',
    'pam': 'pamela',
    'deb': 'deborah', 'debbie': 'deborah',
    'barb': 'barbara', 'barbie': 'barbara',
    'meg': 'margaret', 'maggie': 'margaret', 'peggy': 'margaret', 'marge': 'margaret',
    'nancy': 'ann', 'nan': 'ann',
    'becky': 'rebecca', 'becca': 'rebecca',
    'chris': 'christine', 'chrissie': 'christine', 'christy': 'christine',
    'cindy': 'cynthia',
    'connie': 'constance',
    'dolly': 'dorothy', 'dot': 'dorothy',
    'gail': 'abigail', 'abby': 'abigail',
    'jill': 'jillian',
    'jo': 'joanne', 'josie': 'josephine',
    'judy': 'judith',
    'mandy': 'amanda',
    'patty': 'patricia', 'trish': 'patricia', 'tricia': 'patricia',
    'sandy': 'sandra',
    'steph': 'stephanie', 'steffi': 'stephanie',
    'vicky': 'victoria', 'vikki': 'victoria',
    'wendy': 'gwendolyn',
}

# Common titles to remove
TITLES = [
    'mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'professor',
    'hon', 'honorable', 'rev', 'reverend', 'sir', 'dame',
    'capt', 'captain', 'col', 'colonel', 'gen', 'general',
    'adm', 'admiral', 'lt', 'lieutenant', 'cmdr', 'commander',
]

# Common suffixes to remove
SUFFIXES = [
    'jr', 'sr', 'ii', 'iii', 'iv', 'v', 'vi',
    'phd', 'md', 'esq', 'esquire', 'cpa', 'jd',
    'dds', 'dvm', 'pharmd', 'edd', 'mba',
]


class NameStandardizer:
    """
    Standardizes director names for consistent matching across filings.

    Features:
    - Expands common nicknames to formal names
    - Removes titles and suffixes
    - Normalizes middle initials
    - Handles hyphenated and apostrophe names
    - Creates consistent format: "Firstname [Middle] Lastname"
    """

    def __init__(self,
                 expand_nicknames: bool = True,
                 remove_titles: bool = True,
                 remove_suffixes: bool = True,
                 normalize_middle: bool = True):
        """
        Initialize the name standardizer.

        Args:
            expand_nicknames: Expand nicknames to formal names
            remove_titles: Remove titles like Mr., Dr., etc.
            remove_suffixes: Remove suffixes like Jr., PhD, etc.
            normalize_middle: Standardize middle name/initial handling
        """
        self.expand_nicknames = expand_nicknames
        self.remove_titles = remove_titles
        self.remove_suffixes = remove_suffixes
        self.normalize_middle = normalize_middle

    def standardize(self, name: str) -> Optional[str]:
        """
        Standardize a director name.

        Args:
            name: Raw name string (e.g., "Dr. Robert 'Bob' Smith Jr.")

        Returns:
            Standardized name (e.g., "Robert Smith") or None if invalid
        """
        if not name or not isinstance(name, str):
            return None

        # Basic cleaning
        name = name.strip()
        if not name:
            return None

        # Remove parenthetical content (e.g., ages, birth years)
        name = re.sub(r'\([^)]*\)', '', name)

        # Remove quotes around nicknames, but keep apostrophes inside
        # names (O'Brien, D'Angelo)
        name = name.replace('"', '')
        name = re.sub(r"(?<![^\W\d_])'|'(?![^\W\d_])", '', name)

        # Convert to lowercase for processing
        name_lower = name.lower()

        # Split into parts
        parts = name_lower.split()
        if not parts:
            return None

        # Remove titles
        if self.remove_titles:
            parts = [p for p in parts if p.rstrip('.') not in TITLES]

        # Remove suffixes
        if self.remove_suffixes:
            parts = [p for p in parts if p.rstrip('.') not in SUFFIXES]

        if len(parts) < 2:
            # Need at least first and last name
            return None

        # Extract first, middle, and last name
        first = parts[0]
        last = parts[-1]
        middle_parts = parts[1:-1] if len(parts) > 2 else []

        # "L. John Doerr" goes by John: when the middle name is dropped,
        # promote it over a leading initial so matches line up across filings.
        if (not self.normalize_middle and len(first.rstrip('.')) == 1
                and middle_parts and len(middle_parts[0].rstrip('.')) > 1):
            first = middle_parts[0]
            middle_parts = middle_parts[1:]

        # Expand nicknames in first name
        if self.expand_nicknames and first in NICKNAME_MAP:
            first = NICKNAME_MAP[first]

        # Expand nicknames in middle names
        if self.expand_nicknames:
            middle_parts = [
                NICKNAME_MAP.get(m, m) for m in middle_parts
            ]

        # Normalize middle names/initials
        if self.normalize_middle and middle_parts:
            # Keep only first middle name/initial
            middle = middle_parts[0]
            # If it's just an initial, keep it; otherwise use full name
            if len(middle) == 1 or (len(middle) == 2 and middle.endswith('.')):
                middle = middle.rstrip('.').upper()
            else:
                middle = middle.capitalize()
        else:
            middle = None

        # Capitalize properly (handle hyphenated and apostrophe names)
        first = self._capitalize_name_part(first)
        last = self._capitalize_name_part(last)

        # Build standardized name
        if middle:
            return f"{first} {middle} {last}"
        else:
            return f"{first} {last}"

    def _capitalize_name_part(self, part: str) -> str:
        """
        Properly capitalize a name part, handling special cases.

        Args:
            part: Name part (e.g., "o'brien", "mary-jane")

        Returns:
            Capitalized name part (e.g., "O'Brien", "Mary-Jane")
        """
        # Handle hyphenated names
        if '-' in part:
            return '-'.join(p.capitalize() for p in part.split('-'))

        # Handle apostrophe names (e.g., O'Brien, D'Angelo)
        if "'" in part:
            parts = part.split("'")
            # Capitalize first part normally, second part always uppercase first letter
            return f"{parts[0].capitalize()}'{parts[1].capitalize()}"

        # Handle names starting with Mc. "Mac" is deliberately not special-cased:
        # it is ambiguous (Macdonald vs. Macy, Mace) and would split matches.
        if part.startswith('mc') and len(part) > 2:
            return 'Mc' + part[2:].capitalize()

        # Standard capitalization
        return part.capitalize()

    def standardize_batch(self, names: list) -> dict:
        """
        Standardize a batch of names.

        Args:
            names: List of raw name strings

        Returns:
            Dict mapping raw names to standardized names
        """
        return {
            name: self.standardize(name)
            for name in names
        }


def standardize_name(name: str) -> Optional[str]:
    """
    Convenience function to standardize a single name with default settings.

    Args:
        name: Raw name string

    Returns:
        Standardized name or None
    """
    standardizer = NameStandardizer()
    return standardizer.standardize(name)
