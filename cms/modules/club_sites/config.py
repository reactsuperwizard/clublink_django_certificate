from collections import OrderedDict

PAGE_TEMPLATES = {
    '*': {
        'snippets': OrderedDict([
            ('heading_1', 'char',),
            ('copy_1', 'html',),
            ('heading_2', 'char',),
            ('copy_2', 'html',),
            ('heading_3', 'char',),
            ('copy_3', 'html',),
        ]),
        'images': OrderedDict([
            ('header', {
                'label': 'Header'
            },),
            ('footer-image', {
                'label': 'Footer'
            },),
        ]),
    },
    '': {
        'snippets': {},
        'images': OrderedDict([
            ('splash', {
                'label': 'Splash'
            },),
            ('about-bg', {
                'label': 'About The Club Tile'
            },),
            ('membership-bg', {
                'label': 'Membership Tile'
            },),
            ('events-bg', {
                'label': 'Events Tile'
            },),
            ('daily-fee-bg', {
                'label': 'Daily Fee Golf Tile'
            },),
            ('mp-news-bg', {
                'label': 'My News Tile (Member Portal)'
            },),
            ('mp-club-bg', {
                'label': 'My Club Tile (Member Portal)'
            },),
            ('mp-account-bg', {
                'label': 'My Account Tile (Member Portal)'
            },),
            ('mp-host-event-bg', {
                'label': 'Host My Event Tile (Member Portal)'
            },),
        ]),
    },
    'events': {
        'images': OrderedDict([
            ('header', {
                'label': 'Header'
            },),
            ('footer-image', {
                'label': 'Footer'
            },),
            ('tile_1', {
                'label': 'First Tile'
            },),
            ('tile_2', {
                'label': 'Second Tile'
            },),
            ('tile_3', {
                'label': 'Third Tile'
            },),
            ('tile_4', {
                'label': 'Fourth Tile'
            },),
        ]),
    }
}
