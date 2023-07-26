import os
import qrcode
import base64
import crc8
from io import BytesIO
from django import template
from requests.models import PreparedRequest
from weasyprint import HTML, CSS


def get_crc8_url(url):
    hash = crc8.crc8()
    hash.update(url.encode("utf-8"))
    url += "&cr={}".format(str(int(hash.hexdigest(), 16)).rjust(3, "0"))
    return url


def create_qr_base64(invoice, tbai_id, subject):
    request = PreparedRequest()
    params = {
        "id": tbai_id,
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


def get_html_string(invoice, tbai_id, subject):
    t = template.loader.get_template("PDF/ticketbai.html")
    context = {
        "qr_base64": create_qr_base64(invoice, tbai_id, subject).decode(
            "utf-8"
        ),
        "subject_name": subject["name"],
        "entity_id": subject["entity_id"],
        "invoice": invoice,
        "tbai_id": tbai_id,
    }
    html = t.render(context)
    return html


def build_pdf(invoice, tbai_id, subject):
    css = CSS(string=get_css_string())
    html = HTML(string=get_html_string(invoice, tbai_id, subject))
    return html.write_pdf(stylesheets=[css])
