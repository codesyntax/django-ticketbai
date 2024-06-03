import os
import io
import qrcode
import base64
import crc8
from io import BytesIO
from django import template
from django.utils import translation
from requests.models import PreparedRequest
from django.conf import settings
from weasyprint import HTML, CSS
from PIL import Image


def get_crc8_url(url):
    hash = crc8.crc8()
    hash.update(url.encode("utf-8"))
    url += "&cr={}".format(str(int(hash.hexdigest(), 16)).rjust(3, "0"))
    return url


def create_qr_base64(invoice, subject):
    request = PreparedRequest()
    params = {
        "id": invoice.tbai_code,
        "s": invoice.serial_code,
        "nf": invoice.num,
        "i": invoice.total_amount,
    }
    request.prepare_url(subject["qr_api"], params)

    crc8_url = get_crc8_url(request.url)
    qr_code = qrcode.QRCode(box_size=3)
    qr_code.add_data("%s" % crc8_url)
    img = qr_code.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img.close()
    return base64.b64encode(buffered.getvalue())


def get_css_string():
    t = template.loader.get_template("PDF/ticketbai.css")
    css = t.render()
    return css


def get_html_string(invoice, subject, logo=None, style=None):
    t = template.loader.get_template("PDF/ticketbai.html")
    context = {
        "qr_base64": create_qr_base64(invoice, subject).decode("utf-8"),
        "subject_name": subject["name"],
        "subject_address": subject["address"],
        "entity_id": subject["entity_id"],
        "invoice": invoice,
    }
    if style:
        context.update({"style": style})
    if logo:
        logo_path = os.path.join(settings.STATIC_ROOT, logo)
        with Image.open(logo_path) as image_file:
            width, height = image_file.size
            new_height = int(200 * height / width)
            image_file = image_file.resize((200, new_height), Image.LANCZOS)
            img_bytes = io.BytesIO()
            image_file.save(img_bytes, format='PNG')
            encoded_logo = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            context.update({"logo": encoded_logo})
    translation.activate(invoice.lang)
    html = t.render(context)
    translation.deactivate()
    return html


def build_pdf(invoice, subject, config):
    css = CSS(string=get_css_string())
    html = HTML(string=get_html_string(invoice, subject, config.logo))
    return html.write_pdf(stylesheets=[css])
