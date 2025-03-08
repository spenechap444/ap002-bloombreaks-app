from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from email.header import Header
import smtplib
import os
import logging


class Email:
    def __init__(self, sender):
        self.__sender = sender

    def send_mail(self, p_recip_i, p_subject_i, p_msgbody_i):
        msg = MIMEMultipart()
        msg['From'] = self.__sender
        msg['To'] = p_recip_i
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = Header(p_subject_i, 'utf-8')
        html = f'<html> {p_msgbody_i}'
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.connect('smtp.gmail.com')
            server.ehlo() # preparing the client
            server.starttls() # secure the connection using TLS
            server.sendmail(self.__sender, p_recip_i, msg.as_string())

    def craft_validation_msg(self, p_sec_cd_i) -> str:
        # prepare the html body
        html = '<h1 style="font-size: 24px; font-weight: bold;"> Verify your email</h1>'
        html+= '''<p> Thank you for creating an account with Bloom breaks! </p>
                  <p> Please enter this code in the Bloombreaks app to continue! </p>'''
        html+= f'<h2 style="font-size: 20px; font-weight: bold;"> {p_sec_cd_i}</h2>'

        return html