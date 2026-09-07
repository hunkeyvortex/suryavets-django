"""Conservative extraction and allowlisted image migration. No product matching by name."""
import io
import re
import ssl
import truststore
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from PIL import Image, ImageOps


class DescriptionText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('p', 'br', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'tr'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def nutrition_sections(html):
    """Extract explicitly headed text for staff review, never infer nutrients or units."""
    parser = DescriptionText(); parser.feed(html or '')
    result = {'ingredients': [], 'nutrition_information': []}
    active = None
    headers = {'ingredients': 'ingredients', 'composition': 'ingredients', 'guaranteed analysis': 'nutrition_information',
               'analytical constituents': 'nutrition_information', 'nutritional analysis': 'nutrition_information',
               'nutritional information': 'nutrition_information', 'nutritional additives': 'nutrition_information'}
    for raw in ''.join(parser.parts).splitlines():
        line = ' '.join(raw.split()).strip()
        if not line:
            continue
        heading, sep, rest = line.partition(':')
        key = heading.strip().lower()
        if key in headers:
            active = headers[key]
            result[active].append(line)
        elif (line.endswith(':') or re.match(r'^(feeding|dosage|directions|benefits|precautions|warnings|storage|indications|usage|how to use)\b', line, re.I)):
            active = None
        elif active:
            result[active].append(line)
    return {key: '\n'.join(lines) for key, lines in result.items()}


def image_identity(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, '', ''))


def allowed_image_url(url):
    parts = urlsplit(url)
    return parts.scheme == 'https' and parts.hostname == 'cdn.shopify.com' and not parts.username and not parts.password and parts.port in (None, 443) and parts.path.startswith('/s/files/')


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_image_url(newurl):
            raise ValueError('Image redirected outside the permitted Shopify CDN')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_image(url):
    if not allowed_image_url(url):
        raise ValueError('Source is not an approved Shopify CDN image URL')
    # Native OS trust validation; do not disable hostname/certificate checks.
    opener = build_opener(SafeRedirect(), HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)))
    request = Request(url, headers={'User-Agent': 'SuryaVets-owned-store-media-migration/1.0'})
    with opener.open(request, timeout=15) as response:
        data = response.read(12 * 1024 * 1024 + 1)
    if len(data) > 12 * 1024 * 1024:
        raise ValueError('Image exceeds 12 MB download limit')
    return optimize_image(data)


def optimize_image(data):
    """Shared encoder for migrated images and validated staff uploads."""
    with Image.open(io.BytesIO(data)) as original:
        if original.width * original.height > 20000000:
            raise ValueError('Image exceeds 20 megapixels')
        if original.format not in {'JPEG', 'PNG', 'WEBP', 'GIF'}:
            raise ValueError('Unsupported image format')
        original.load()
        picture = ImageOps.exif_transpose(original).convert('RGBA' if 'A' in original.getbands() or 'transparency' in original.info else 'RGB')
        outputs = []
        for edge in (1400, 360):
            resized = picture.copy(); resized.thumbnail((edge, edge))
            stream = io.BytesIO(); resized.save(stream, 'WEBP', quality=88, method=4)
            outputs.append(stream.getvalue())
    return outputs
