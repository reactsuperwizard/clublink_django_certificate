import re, logging

from io import BytesIO

from django.contrib.staticfiles import finders
from django.core.files.storage import default_storage
from django.template.defaultfilters import date as datefilter
from django.utils import translation
from django.utils.translation import ugettext as _
from PIL import Image
from reportlab.graphics.barcode import code128
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from clublink.base.utils import sanitize_string


class AbstractCertificateGenerator(object):
    DEFAULT_FONT_SIZE = None
    DEFAULT_STYLE = None
    FONTS = {}
    PARAGRAPH_STYLES = {}

    def __init__(self, certificate, **kwargs):
        self.certificate = certificate

        # Create the canvas
        self.buffer = BytesIO()
        self.pagesize = kwargs.get('pagesize', LETTER)
        self.canvas = canvas.Canvas(self.buffer, pagesize=self.pagesize, pageCompression=1)
        self.canvas.setTitle(kwargs.get('title', _('ClubLink Gift Certificate')))

        # Register the fonts
        for name, path in self.FONTS.items():
            pdfmetrics.registerFont(TTFont(name, path))

        # Add the styles
        self.styles = getSampleStyleSheet()

        for name, details in self.PARAGRAPH_STYLES.items():
            self.styles.add(ParagraphStyle(name, **details))

    def resize_image(self, path, size):
        img = Image.open(path)
        img.thumbnail(size)
        return ImageReader(img)

    def read_image(self, image):

        from django.core.cache import cache
        img = cache.get(image.name)
        if not img:
            img = Image.open(default_storage.open(image.name))
            cache.set(image.name, img)
        return ImageReader(img)

    def print_paragraphs(self, message, offset, x, width, **kwargs):
        style = self.styles[kwargs.get('style', self.DEFAULT_STYLE)]

        for para in message.split('\n\n'):
            p = Paragraph(para.replace('\n', '<br/>'), style=style)
            p.wrapOn(self.canvas, width, self.pagesize[1])

            h = p.height
            p.drawOn(self.canvas, x, self.pagesize[1] - offset - h)
            offset += h + (0.1 * inch)

        return offset

    def format_message(self, message):
        c = self.certificate
        if c.type.category == c.type.MERCHANDISE_CATEGORY:
            quantity = c.quantity
        elif c.type.category == c.type.RAIN_CHECK_CATEGORY:
            quantity = '{0:.2f}'.format(round(float(c.quantity) + float(c.tax), 2))
        else:
            quantity = int(c.quantity)
        return message.format(quantity=quantity, power_cart=c.get_power_cart_display())

    def fix_barcode_value(self, value):
        return re.sub('[^0-9]', '', value).zfill(13)

    def prepare_pdf(self):
        raise NotImplementedError()

    def generate(self):
        curr_lang = translation.get_language()
        translation.activate(self.certificate.batch.language)
        self.prepare_pdf()
        if curr_lang:
            translation.activate(curr_lang)

    def render(self):
        self.canvas.showPage()
        self.canvas.save()

        pdf = self.buffer.getvalue()
        self.buffer.close()

        return pdf


class DefaultCertificateGenerator(AbstractCertificateGenerator):
    DEFAULT_FONT_SIZE = 10

    DEFAULT_STYLE = 'Gotham-Light'

    FONTS = {
        'Garamond': finders.find('certificates/fonts/Garamond.ttf'),
        'Gotham-Light': finders.find('certificates/fonts/Gotham-Light.ttf'),
        'Gotham-Medium': finders.find('certificates/fonts/Gotham-Medium.ttf'),
    }

    PARAGRAPH_STYLES = {
        DEFAULT_STYLE: {
            'fontName': 'Gotham-Light',
            'fontSize': DEFAULT_FONT_SIZE,
            'leading': DEFAULT_FONT_SIZE + 3,
        },
        'Gotham-Medium': {
            'fontName': 'Gotham-Medium',
            'fontSize': DEFAULT_FONT_SIZE,
            'leading': DEFAULT_FONT_SIZE + 3,
        },
    }

    def prepare_pdf(self):
        from clublink.certificates.models import CertificateType

        cert = self.certificate

        effective_header = cert.effective_header
        if effective_header:
            header_img = self.read_image(effective_header)
        else:
            img = 'certificate-header-double.jpg' if cert.club_secondary else 'certificate-header.jpg'
            header_img = finders.find('certificates/{}'.format(img))

        # Draw the header image
        self.canvas.drawImage(
            header_img,
            x=0,
            y=self.pagesize[1] - (1.883 * inch),
            width=self.pagesize[0],
            height=1.883 * inch)

        # Draw the logo(s)
        if cert.type.category == CertificateType.PLAYERS_CLUB_CATEGORY:
            logo_file = finders.find('certificates/players-club-logo.png')
        elif cert.type.category == CertificateType.MERCHANDISE_CATEGORY:
            logo_file = finders.find('certificates/cl-logo-{}.png'.format(cert.batch.language))
        else:
            try:
                logo_file = default_storage.open(cert.club.logo.name)
            except:
                logo_file = finders.find('certificates/logo-25.jpg')

        if cert.club.logo or cert.type.category in (CertificateType.PLAYERS_CLUB_CATEGORY,
                                                    CertificateType.MERCHANDISE_CATEGORY):
            self.canvas.drawImage(
                self.resize_image(logo_file, (300, 300)),
                x=0.487 * inch,
                y=9.753 * inch,
                width=1.107 * inch,
                height=1.107 * inch,
                mask='auto',
                preserveAspectRatio=True)

        if (cert.club_secondary and cert.club_secondary != cert.club and cert.club_secondary.logo
                and cert.type.category not in (CertificateType.PLAYERS_CLUB_CATEGORY,
                                               CertificateType.MERCHANDISE_CATEGORY)):
            try:
                logo_file = default_storage.open(cert.club_secondary.logo.name)
            except:
                logo_file = finders.find('certificates/logo-25.jpg')

            self.canvas.drawImage(
                self.resize_image(logo_file, (300, 300)),
                x=6.906 * inch,
                y=9.753 * inch,
                width=1.107 * inch,
                height=1.107 * inch,
                mask='auto',
                preserveAspectRatio=True)

        # Headline
        self.canvas.setFillColorRGB(1, 1, 1)

        headline_font_size = 26
        cert_name = cert.type.localized('name', cert.batch.language)
        while pdfmetrics.stringWidth(cert_name, 'Garamond', headline_font_size) > 4.25 * inch:
            headline_font_size -= 0.1

        self.canvas.setFont('Garamond', headline_font_size)
        self.canvas.drawCentredString(4.25 * inch, 9.78 * inch, cert_name)

        # Define text styles
        self.canvas.setFillColorRGB(0, 0, 0)

        # Member Details
        y_offset = 2.25 * inch

        if not cert.type.hide_recipient_name:
            y_offset = self.print_paragraphs(
                _('NAME: {name}').format(name=cert.batch.recipient_name),
                offset=y_offset + (0.25 * inch),
                x=0.35 * inch,
                width=3.747 * inch)

        # Message to recipient
        message = cert.message
        if not message:
            message = cert.type.localized('message', cert.batch.language)
        message = self.format_message(sanitize_string(message))

        if message:
            y_offset = self.print_paragraphs(
                message,
                offset=y_offset + (0.25 * inch),
                x=0.35 * inch,
                width=3.747 * inch)

        # Restrictions
        if cert.type.category != CertificateType.LEFT_SIDE_CUSTOM:
            restrictions = self.format_message(
                sanitize_string(
                    cert.type.localized('restrictions', cert.batch.language)))


            self.print_paragraphs(
                restrictions,
                offset=y_offset + (0.25 * inch),
                x=0.35 * inch,
                width=3.747 * inch)

        # Divider
        self.canvas.setStrokeColorRGB(0, 0, 0)
        self.canvas.setLineWidth(0.0035 * inch)
        self.canvas.line(4.443 * inch, 8.475 * inch, 4.443 * inch, 5.79 * inch)

        # Expiry Date
        y_offset = 2.25 * inch

        if cert.expiry_date:
            y_offset = self.print_paragraphs(
                _('CERTIFICATE EXPIRES:'),
                offset=y_offset + (0.25 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Medium')

            y_offset = self.print_paragraphs(
                datefilter(cert.expiry_date, 'F j, Y').upper(),
                offset=y_offset - (0.1 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Light')

        # Club Details
        if cert.type.category in (
            CertificateType.PLAYERS_CLUB_CATEGORY,
            CertificateType.MERCHANDISE_CATEGORY):
            title = _('CLUBS:')
        elif cert.type.category == CertificateType.RESORT_STAY_CATEGORY:
            title = _('RESORT:')
        else:
            title = _('CLUB:')

        y_offset = self.print_paragraphs(
            title,
            offset=y_offset + (0.25 * inch),
            x=4.81 * inch,
            width=3.357 * inch,
            style='Gotham-Medium')


        if cert.type.category == CertificateType.PLAYERS_CLUB_CATEGORY:
            for club in cert.type.players_club_clubs.all():
                daily_fee = cert.type.players_club_daily_fee_listing and club.daily_fee_location
                name_str = '{} - Daily Fee' if daily_fee else '{}'
                y_offset = self.print_paragraphs(
                    name_str.format(club.name),
                    offset=y_offset - (0.1 * inch),
                    x=4.81 * inch,
                    width=3.357 * inch)
        elif cert.type.category == CertificateType.MERCHANDISE_CATEGORY:
            y_offset = self.print_paragraphs(
                _('ClubLink Wide<br /> All Canadian locations'),
                offset=y_offset - (0.1 * inch),
                x=4.81 * inch,
                width=3.357 * inch)
        else:

            club_details = cert.club.name

            if cert.club.address:
                club_details += ', <br />{}'.format(cert.club.address)

            if cert.club.city and cert.club.state:
                club_details += ', <br />{}, {}'.format(cert.club.city, cert.club.state)

            y_offset = self.print_paragraphs(
                club_details,
                offset=y_offset - (0.1 * inch),
                x=4.81 * inch,
                width=3.357 * inch)

            if cert.club_secondary and (cert.club_secondary != cert.club):
                club_details = '{}, <br />{}, <br />{}, {}'.format(
                    cert.club_secondary.name, cert.club_secondary.address,
                    cert.club_secondary.city, cert.club_secondary.state)

                y_offset = self.print_paragraphs(
                    title,
                    offset=y_offset + (0.25 * inch),
                    x=4.81 * inch,
                    width=3.357 * inch,
                    style='Gotham-Medium')

                y_offset = self.print_paragraphs(
                    club_details,
                    offset=y_offset - (0.1 * inch),
                    x=4.81 * inch,
                    width=3.357 * inch)

            # output_str = '{} <br/>'.format(cert.club.name)

            # # if cert.club_secondary:
            # #     output_str + '{} <br/>'.format(
            # #         cert.club_secondary.name
            # #     )

            # y_offset = self.print_paragraphs(
            #     output_str,
            #     offset=y_offset - (0.1 * inch),
            #     x=4.81 * inch,
            #     width=3.357 * inch,
            #     style='Gotham-Light')

        # Num Players
        if cert.num_players:
            y_offset = self.print_paragraphs(
                _('NUMBER OF PLAYERS:'),
                offset=y_offset + (0.25 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Medium')

            y_offset = self.print_paragraphs(
                str(int(cert.num_players)),
                offset=y_offset - (0.1 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Light')

        # Num Nights
        if cert.num_nights:
            y_offset = self.print_paragraphs(
                _('NUMBER OF NIGHTS:'),
                offset=y_offset + (0.25 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Medium')

            y_offset = self.print_paragraphs(
                str(int(cert.num_nights)),
                offset=y_offset - (0.1 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Light')

        # Dollar Amount
        if cert.dollar_amount:
            y_offset = self.print_paragraphs(
                _('DOLLAR AMOUNT:'),
                offset=y_offset + (0.25 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Medium')

            y_offset = self.print_paragraphs(
                str(cert.dollar_amount),
                offset=y_offset - (0.1 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Light')

        # Redemption Details
        redemption_details = cert.type.localized('redemption_details', cert.batch.language)
        if redemption_details:
            y_offset = self.print_paragraphs(
                '{}:'.format(cert.type.get_redemption_location_display().upper()),
                offset=y_offset + (0.25 * inch),
                x=4.81 * inch,
                width=3.357 * inch,
                style='Gotham-Medium')

            self.print_paragraphs(
                sanitize_string(redemption_details),
                offset=y_offset - (0.1 * inch),
                x=4.81 * inch,
                width=3.357 * inch)

        # ClubLink Logo
        self.canvas.drawImage(
            finders.find('certificates/cl-logo-{}.png'.format(cert.batch.language)),
            x=4.793 * inch,
            y=3.517 * inch,
            width=1.2* inch,
            height=0.35 * inch,
            mask='auto',
            preserveAspectRatio=True)

        # Barcode
        code = self.fix_barcode_value(cert.code)
        barcode = code128.Code128(code, barHeight=0.4 * inch, barWidth=0.01 * inch)
        barcode.drawOn(
            self.canvas,
            x=(8.15 * inch) - barcode.width,
            y=3.65 * inch)

        self.canvas.setFont('Courier', 10)
        self.canvas.drawCentredString(
            text=code,
            x=(8.15 * inch) - (barcode.width / 2),
            y=3.517 * inch)

        # Footer text
        self.canvas.setFont('Gotham-Medium', 9)

        self.canvas.drawCentredString(
            text=_('This certificate is valid for one time use only and must be presented at the '
                   'time of redemption.'),
            x=4.25 * inch,
            y=2.953 * inch)

        self.canvas.drawCentredString(
            text=_('ClubLink is not responsible for lost, stolen, or duplicate certificates.'),
            x=4.25 * inch,
            y=2.783 * inch)

        # Divider
        self.canvas.setStrokeColorRGB(0, 0, 0)
        self.canvas.setLineWidth(0.005 * inch)
        self.canvas.line(0.35 * inch, 2.565 * inch, 8.15 * inch, 2.565 * inch)

        # Advertisement
        if cert.type.advertisement:
            try:
                ad = cert.type.advertisement
                image = ad.image if cert.batch.language == 'en' else ad.image_fr
                self.canvas.drawImage(
                    self.read_image(image),
                    x=0.35 * inch,
                    y=0.35 * inch,
                    width=7.80 * inch,
                    height=2.1 * inch,
                    preserveAspectRatio=True)
            except:
                logging.error('Could not draw ad')


class AG30CertificateGenerator(AbstractCertificateGenerator):
    DEFAULT_FONT_SIZE = 12

    DEFAULT_STYLE = 'body'

    FONTS = {
        'SourceSansPro-Light': finders.find('certificates/fonts/SourceSansPro-Light.ttf'),
        'SourceSansPro-LightIt': finders.find('certificates/fonts/SourceSansPro-LightIt.ttf'),
        'SourceSansPro-Semibold': finders.find('certificates/fonts/SourceSansPro-Semibold.ttf'),
    }

    PARAGRAPH_STYLES = {
        DEFAULT_STYLE: {
            'fontName': 'SourceSansPro-Light',
            'fontSize': DEFAULT_FONT_SIZE,
            'leading': DEFAULT_FONT_SIZE + 3,
        },
        'body-bold': {
            'fontName': 'SourceSansPro-Semibold',
            'fontSize': DEFAULT_FONT_SIZE,
            'leading': DEFAULT_FONT_SIZE + 6,
        },
        'body-italic': {
            'fontName': 'SourceSansPro-LightIt',
            'fontSize': DEFAULT_FONT_SIZE - 3,
            'leading': DEFAULT_FONT_SIZE + 3,
        },
        'fineprint': {
            'fontName': 'SourceSansPro-LightIt',
            'fontSize': DEFAULT_FONT_SIZE - 4,
            'leading': DEFAULT_FONT_SIZE,
        },
        'featured': {
            'fontName': 'SourceSansPro-Semibold',
            'fontSize': DEFAULT_FONT_SIZE + 2,
            'leading': DEFAULT_FONT_SIZE + 8,
        },
        'headline': {
            'fontName': 'SourceSansPro-Semibold',
            'fontSize': DEFAULT_FONT_SIZE + 8,
            'leading': DEFAULT_FONT_SIZE + 11,
            'textColor': HexColor(0xC2940B)
        },
    }

    def prepare_pdf(self):
        from clublink.certificates.models import CertificateType

        cert = self.certificate

        effective_header = cert.effective_header
        if effective_header:
            header_img = self.read_image(effective_header)
        else:
            header_img = finders.find('certificates/ag30-header-{}.jpg'.format(cert.batch.language))

        # Header Image
        self.canvas.drawImage(
            header_img,
            x=0.35 * inch,
            y=self.pagesize[1] - (3.537 * inch),
            width=self.pagesize[0] - (0.7 * inch),
            height=3.187 * inch,
            preserveAspectRatio=True)

        # Headline
        CONTENT_TOP = 3.787 * inch

        y_offset = self.print_paragraphs(
            _('YOUR 30-DAY CLUBLINK MEMBERSHIP EXPERIENCE AWAITS.'),
            offset=CONTENT_TOP,
            x=0.35 * inch,
            width=5.36 * inch,
            style='headline')

        # Body

        y_offset = self.print_paragraphs(
            _('With access to over 40* courses in Ontario and Quebec along with the many other '
              'benefits of a ClubLink membership including:'),
            offset=y_offset,
            x=0.35 * inch,
            width=5.36 * inch,
            style='body-bold')

        message = _("""
            •\tTee time booking privileges up to seven days in advance

            •\tAccount privileges

            •\tClubLink Advantage Pricing on golf merchandise

            •\tPreferred access and discounts at ClubLink resorts in Muskoka

            •\tComplimentary use of practice facilities (excluding Glen Abbey)

            •\tAccess to dining at all locations
            """)

        y_offset = self.print_paragraphs(
            message,
            offset=y_offset - (0.2 * inch),
            x=0.35 * inch,
            width=5.36 * inch)

        y_offset = self.print_paragraphs(
            _('* An additional fee applies to play golf at Glen Abbey, RattleSnake Point, '
              'Greystone and King Valley.'),
            offset=y_offset + (0.15 * inch),
            x=0.35 * inch,
            width=5.36 * inch,
            style='body-italic')

        message = cert.message
        if not message:
            message = cert.type.localized('message', cert.batch.language)
        message = self.format_message(sanitize_string(message))

        self.print_paragraphs(
            message,
            offset=y_offset,
            x=0.35 * inch,
            width=5.36 * inch,
            style='body-bold')

        # Sidebar

        y_offset = self.print_paragraphs(
            _('Certificate: <br/>{code}').format(code=cert.code),
            offset=CONTENT_TOP,
            x=6.06 * inch,
            width=2.09 * inch,
            style='featured')

        if cert.expiry_date:
            y_offset = self.print_paragraphs(
                _('Membership must be activated by: <br/>{date}').format(
                    date=datefilter(cert.expiry_date, 'j/n/Y')),
                offset=y_offset + (0.15 * inch),
                x=6.06 * inch,
                width=2.09 * inch,
                style='featured')

        if cert.type.category != CertificateType.LEFT_SIDE_CUSTOM:
            restrictions = self.format_message(sanitize_string(
                cert.type.localized('restrictions', cert.batch.language)))

            self.print_paragraphs(
                restrictions,
                offset=y_offset + (0.15 * inch),
                x=6.06 * inch,
                width=2.09 * inch,
                style='fineprint')

        # Divider
        self.canvas.setStrokeColorRGB(0, 0, 0)
        self.canvas.setLineWidth(0.005 * inch)
        self.canvas.line(0.35 * inch, 2.565 * inch, 8.15 * inch, 2.565 * inch)

        # Advertisement
        if cert.type.advertisement:
            ad = cert.type.advertisement
            try:
                image = ad.image if cert.batch.language == 'en' else ad.image_fr
                self.canvas.drawImage(
                    self.read_image(image),
                    x=0.35 * inch,
                    y=0.35 * inch,
                    width=7.80 * inch,
                    height=2.1 * inch,
                    preserveAspectRatio=True)
            except:
                logging.error('Could not draw ad')


class Prestige50CertificateGenerator(AbstractCertificateGenerator):
    DEFAULT_FONT_SIZE = 12

    DEFAULT_STYLE = 'body'

    FONTS = {
        'SourceSansPro-Light': finders.find('certificates/fonts/SourceSansPro-Light.ttf'),
        'SourceSansPro-LightIt': finders.find('certificates/fonts/SourceSansPro-LightIt.ttf'),
        'SourceSansPro-Semibold': finders.find('certificates/fonts/SourceSansPro-Semibold.ttf'),
    }

    PARAGRAPH_STYLES = {
        DEFAULT_STYLE: {
            'fontName': 'SourceSansPro-Light',
            'fontSize': DEFAULT_FONT_SIZE,
            'leading': DEFAULT_FONT_SIZE + 6,
        },
        'sidebar-bold': {
            'fontName': 'SourceSansPro-Semibold',
            'fontSize': DEFAULT_FONT_SIZE,
            'leading': DEFAULT_FONT_SIZE + 6,
        },
        'sidebar': {
            'fontName': 'SourceSansPro-Light',
            'fontSize': DEFAULT_FONT_SIZE - 1,
            'leading': DEFAULT_FONT_SIZE + 3,
        },
        'headline': {
            'fontName': 'SourceSansPro-Semibold',
            'fontSize': DEFAULT_FONT_SIZE + 8,
            'leading': DEFAULT_FONT_SIZE + 11,
        },
    }

    def prepare_pdf(self):
        cert = self.certificate

        effective_header = cert.effective_header
        if effective_header:
            header_img = self.read_image(effective_header)
        else:
            header_img = finders.find(
                'certificates/prestige50-header.jpg')

        # Header Image
        self.canvas.drawImage(
            header_img,
            x=0.35 * inch,
            y=self.pagesize[1] - (3.537 * inch),
            width=self.pagesize[0] - (0.7 * inch),
            height=3.187 * inch,
            preserveAspectRatio=True)

        # Headline
        CONTENT_TOP = 3.787 * inch

        from .models import CertificateType

        if cert.type.template == CertificateType.GOLF_FOR_LIFE_TEMPLATE:
            msg = ''
        else:
            msg = 'Welcome back for another great season!'

        y_offset = self.print_paragraphs(
            _(msg),
            offset=CONTENT_TOP,
            x=0.35 * inch,
            width=5.2 * inch,
            style='headline')

        #### DO NOT REPEAT YOURSELF ####

        # Body
        message = cert.message
        if not message:
            message = cert.type.localized('message', cert.batch.language)
        message = self.format_message(sanitize_string(message))

        self.print_paragraphs(
            message,
            offset=y_offset + (0.05 * inch),
            x=0.35 * inch,
            width=5.2 * inch)

        # Sidebar
        if cert.expiry_date:
            y_offset = self.print_paragraphs(
                _('Expires: {date}').format(
                    date=datefilter(cert.expiry_date, 'F j, Y')),
                offset=CONTENT_TOP + (0.125 * inch),
                x=6.06 * inch,
                width=2.09 * inch,
                style='sidebar-bold')

        from clublink.certificates.models import CertificateType

        if cert.type.category != CertificateType.LEFT_SIDE_CUSTOM:
            restrictions = self.format_message(
                sanitize_string(
                    cert.type.localized('restrictions', cert.batch.language)))

            y_offset = self.print_paragraphs(
                restrictions,
                offset=y_offset + (0.15 * inch),
                x=6.06 * inch,
                width=2.09 * inch,
                style='sidebar')

        # Barcode
        code = self.fix_barcode_value(cert.code)
        barcode = code128.Code128(code, barHeight=1 * inch, barWidth=0.01 * inch)
        barcode.drawOn(
            self.canvas,
            x=(7.95 * inch) - barcode.width,
            y=(10.75 * inch) - y_offset - barcode.height)

        self.canvas.setFont('Courier', 10)
        self.canvas.drawCentredString(
            text=code,
            x=(7.95 * inch) - (barcode.width / 2),
            y=(10.6 * inch) - y_offset - barcode.height)

        #### END DO NOT REPEAT YOURSELF ####

        # Advertisement
        if cert.type.advertisement:
            ad = cert.type.advertisement
            image = ad.image if cert.batch.language == 'en' else ad.image_fr
            self.canvas.drawImage(
                self.read_image(image),
                x=0.35 * inch,
                y=0.35 * inch,
                width=7.80 * inch,
                height=2.1 * inch,
                preserveAspectRatio=True)
