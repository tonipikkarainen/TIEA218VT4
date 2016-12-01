#!/usr/bin/python
# -*- coding: utf-8 -*-

from functools import wraps
from flask import Flask, session, redirect, url_for, escape, request, Response, render_template, flash
import hashlib
import sqlite3
import logging
import os
import sys
import datetime
import time
#lokitiedosto debuggausta varten
logging.basicConfig(filename='flask.log',level=logging.DEBUG)
    
app = Flask(__name__)
app.secret_key = '7wZ]\x89\xc3z\xb8\x97\xba|\x95\xa2x\xf6lP\xaas\xbf\xe7\x93\xf32'
#m = hashlib.sha512()
# @app.route määrää mille osoitteille tämä funktio suoritetaan
# vaihe 5!!!! 

# Tämä otettu AS IS -pääteohjausesimerkistä.
def auth(f):
    ''' Tämä decorator hoitaa kirjautumisen tarkistamisen ja ohjaa tarvittaessa kirjautumissivulle
    '''
    @wraps(f)
    def decorated(*args, **kwargs):
        # tässä voisi olla monimutkaisempiakin tarkistuksia mutta yleensä tämä riittää
        if not 'kirjautunut' in session:
            return redirect(url_for('kirjaudu'))
        return f(*args, **kwargs)
    return decorated

# Poistaa elokuvan jos voi    
def voikoPoistaaElokuvan(eid,cur):
    sql="""
    SELECT VuokrausPVM 
    FROM Vuokraus
    WHERE ElokuvaID=:eid
    """
    paivat=[]
    try:
        cur.execute(sql, {"eid":eid})
    except:
        logging.debug("virhe")
        logging.debug(sys.exc_info()[0])
    
    for row in cur.fetchall():
        paivat.append(dict(vpvm=row['VuokrausPVM'].decode("UTF-8")))
    #Palauttaa true jos voi poistaa    
    
    return not paivat
   
    
    
    

def connect():
    try:
        con = sqlite3.connect(os.path.abspath('../../hidden/video'))
        con.row_factory = sqlite3.Row
        con.text_factory = str
    except Exception as e:
        logging.debug("Kanta ei aukea")
        # sqliten antama virheilmoitus:
        logging.debug(str(e))
    return con
   
#Suorittaa kyselyn kursorilla   
def teeKysely(sql, virheTeksti, cur):
    try:
        cur.execute(sql)
    except Exception as e:
        logging.debug(virheTeksti)
        logging.debug(str(e))
        
@app.route('/logout') 
def logout():
    session.pop('kirjautunut',None)
    # url_for-metodilla voidaan muodostaa osoite haluttuun funktioon.    
    return redirect(url_for('kirjaudu'))

@app.route('/', methods=['POST','GET']) 
@auth
def etusivu():
   
    con = connect() # avataan yhteys
    cur = con.cursor() # luodaan kursori
    
    sql = """
    SELECT Jasen.nimi AS jasen,Elokuva.Nimi AS elokuva,  Vuokraus.VuokrausPVM AS vpvm,
    Vuokraus.PalautusPVM as ppvm
    FROM Jasen 
    LEFT OUTER JOIN Elokuva
    ON Elokuva.ElokuvaID=Vuokraus.ElokuvaID 
    LEFT OUTER JOIN Vuokraus 
    ON Vuokraus.JasenID=Jasen.JasenID
    ORDER BY Jasen.nimi ASC, Vuokraus.VuokrausPVM ASC
    """
    vuokraukset=[]
    
    teeKysely(sql,"Ei löydy vuokraustietoja",cur)

    
    for row in cur.fetchall():
        if row['vpvm']:
            vuokraukset.append(dict(elokuva=row['elokuva'].decode("UTF-8"),
            jasen=row['jasen'].decode("UTF-8"),vpvm=row['vpvm'].decode("UTF-8"),
            ppvm=row['ppvm'].decode("UTF-8")))
        else: 
            vuokraukset.append(dict(jasen=row['jasen'].decode("UTF-8")))
    con.close()
    return render_template('etusivu.html',vuokraukset=vuokraukset).encode("UTF-8")


# validoi päivämäärän
# oletuksena hyväksyy 1900 ->, miksi? 
# Changed in version 3.2: In previous versions, strftime() method was restricted to years >= 1900.
# Miten voi muuttaa?   
def validoiPvm(text):
    try:
        if datetime.datetime.strptime(text, '%Y-%m-%d') < datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return False
    except: 
        return False
        
    try:
        return text == datetime.datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    except:
        return False
        
        
@app.route('/elokuvat', methods=['POST','GET']) 
@auth
def elokuvat():
 
    con = connect() # avataan yhteys
    cur = con.cursor() # luodaan kursori
    try:
        valittu=request.args.get('valittu')
    except:
        logging.debug("ei valittua")
    
    # Yritin tehdä tätä fiksummin mutta ilmeisesti order by- jälkeen
    # ei voi sijoittaa arvoa näin :valittu
    sql = """
    SELECT Elokuva.nimi AS elokuva,Elokuva.ElokuvaID, Elokuva.Julkaisuvuosi as julkaisuvuosi,
    Elokuva.Arvio as arvio, COUNT(VuokrausPVM) AS vuokraLkm 
    FROM Elokuva 
    LEFT OUTER JOIN Vuokraus
    ON Elokuva.ElokuvaID=Vuokraus.ElokuvaID 
    GROUP BY elokuva
    ORDER BY elokuva
    """
    if valittu=="julkaisuvuosi":
        sql = """
        SELECT Elokuva.nimi AS elokuva,Elokuva.ElokuvaID, Elokuva.Julkaisuvuosi as julkaisuvuosi,
        Elokuva.Arvio as arvio, COUNT(VuokrausPVM) AS vuokraLkm 
        FROM Elokuva 
        LEFT OUTER JOIN Vuokraus
        ON Elokuva.ElokuvaID=Vuokraus.ElokuvaID 
        GROUP BY elokuva
        ORDER BY julkaisuvuosi
        """    
    
    elif valittu=="arvio":
        sql = """
        SELECT Elokuva.nimi AS elokuva,Elokuva.ElokuvaID, Elokuva.Julkaisuvuosi as julkaisuvuosi,
        Elokuva.Arvio as arvio, COUNT(VuokrausPVM) AS vuokraLkm 
        FROM Elokuva 
        LEFT OUTER JOIN Vuokraus
        ON Elokuva.ElokuvaID=Vuokraus.ElokuvaID 
        GROUP BY elokuva
        ORDER BY arvio
        """
    elif valittu=="vuokraLkm":
        sql = """
        SELECT Elokuva.nimi AS elokuva,Elokuva.ElokuvaID, Elokuva.Julkaisuvuosi as julkaisuvuosi,
        Elokuva.Arvio as arvio, COUNT(VuokrausPVM) AS vuokraLkm 
        FROM Elokuva 
        LEFT OUTER JOIN Vuokraus
        ON Elokuva.ElokuvaID=Vuokraus.ElokuvaID 
        GROUP BY elokuva
        ORDER BY vuokraLkm
        """
    
    
    elokuvat=[]
    
    try:
        cur.execute(sql)
    except Exception as e:
        logging.debug("ei onnistunut elokuvalista")
        logging.debug(str(e))

    for row in cur.fetchall():
        elokuvat.append(dict(elokuva=row['elokuva'].decode("UTF-8"), elokuvaid=row['ElokuvaID'],
        vuokraLkm=row['vuokraLkm']))
    
    con.close()
    return render_template('elokuvat.html',elokuvat=elokuvat, valittu=valittu).encode("UTF-8")
    
#Käsittelee uuden elokuvan   
@app.route('/uusielokuva', methods=['POST','GET']) 
@auth
def uusielokuva():
    con=connect()
    cur = con.cursor()
    
    lajityypit=[]

    virhe=""
    
    tayttoVirhe=False
    
    try:
        submit=request.form['laheta'].decode("UTF-8")
    except:
        submit=""
    
    try:
        lajityyppiID=int(request.form['lajityyppi'])
    except:
        lajityyppiID=0
        
    try: 
        nimi=request.form['nimi'].decode("utf-8")
    except:
        nimi=""
        
    try: 
        julkaisuvuosi=int(request.form['julkaisuvuosi'].decode("utf-8"))
    except:
        julkaisuvuosi=""
   
    try: 
        vuokrahinta=float(request.form['vuokrahinta'].decode("utf-8"))
    except:
        vuokrahinta=""
    
    try: 
        arvio=int(request.form['arvio'].decode("utf-8"))
    except:
        arvio=""
    # Tarkastetaan onko kentät täytetty
    if nimi=="" or julkaisuvuosi=="" or vuokrahinta=="" or arvio=="":
        tayttoVirhe=True
    
    
    # Jos ei olla ensimmäistä kertaa tulossa sivulle
    # ja vuokrapäivämäärä on väärin annetaan virhe.
    # Miten saa session katoamaan, jos käyttää "edellinen nappia"??
  
    if submit=="Lisaa uusi elokuva" and tayttoVirhe:
        virhe="Täytä kaikki kentät!".decode("utf-8")
   
   
    
    # Elokuvan lisääminen
    if not tayttoVirhe:
        sql = """
        INSERT INTO elokuva (nimi,julkaisuvuosi,vuokrahinta,arvio,lajityyppiid) 
        VALUES (:nimi,:julkaisuvuosi,:vuokrahinta,:arvio,:LajityyppiID) 
        """
        try:
            cur.execute(sql, {"nimi":nimi,"julkaisuvuosi":julkaisuvuosi,"vuokrahinta":vuokrahinta, 
            "arvio":arvio,"LajityyppiID":lajityyppiID})
            con.commit()
            con.close()
            
            return redirect(url_for('elokuvat')) # palataan etusivulle 
        except:
            logging.debug("ei mennyt elokuva")
            logging.debug(sys.exc_info()[0])
    
    
    #Kyselyt joilla täytetään alasvetolaatikot
    
    sql = """
    SELECT Tyypinnimi as lajityyppi, LajityyppiID as lajiID
    FROM Lajityyppi
    """
    
    teeKysely(sql, "Ei löydy lajityyppia", cur)
    
    for row in cur.fetchall():
        lajityypit.append(dict(lajityyppi=row['lajityyppi'].decode("UTF-8"),lajiID=row['lajiID']))
        
 
    con.close()
    return render_template('uusielokuva.html', lajityypit=lajityypit, virhe=virhe).encode("UTF-8")


#Käsittelee uuden vuokrauksen    
@app.route('/uusivuokraus', methods=['POST','GET']) 
@auth
def uusivuokraus():
    con=connect()
    cur = con.cursor()
    
    elokuvat=[]
    jasenet=[]
    
    virhe=""
    
    #Kysytään vuokra- ja palautuspäivämäärät
    try:
        vuokraPvm = request.form['vuokraPvm'].decode("UTF-8")
    except:
        vuokraPvm = ""
    
    try:
        palautusPvm = request.form['palPvm'].decode("UTF-8")
    except:
        palautusPvm = ""
        
    try:
        elokuvaID=int(request.form['elokuva'])
    except:
        elokuvaID=0
    
    try:
        jasenID=int(request.form['jasen'])
    except:
        jasenID=0
    
    try:
        submit=request.form['laheta'].decode("UTF-8")
    except:
        submit=""
    
    # Jos ei olla ensimmäistä kertaa tulossa sivulle
    # ja vuokrapäivämäärä on väärin annetaan virhe.
    # Miten saa session katoamaan, jos käyttää "edellinen nappia"??
   
    if submit=="Luo uusi vuokraus" and not validoiPvm(vuokraPvm):
        virhe="Päivämäärä väärässä muodossa tai kyseessä jo mennyt päivämäärä, anna muodossa VVVV-KK-PP".decode("utf-8")
   
    
    
    # Vuokrauksen lisääminen
    if validoiPvm(vuokraPvm):
        sql = """
        INSERT INTO vuokraus (jasenid,elokuvaid,vuokrauspvm,palautuspvm) 
        VALUES (:jasenID,:elokuvaID,:vuokraPvm,:palautusPvm) 
        """
        try:
            cur.execute(sql, {"jasenID":jasenID,"elokuvaID":elokuvaID,"vuokraPvm":vuokraPvm, 
            "palautusPvm":palautusPvm})
            con.commit()
            con.close()
            return redirect(url_for('etusivu')) # palataan etusivulle 
        except:
            logging.debug("ei mennyt")
            logging.debug(sys.exc_info()[0])
    
    
    #Kyselyt joilla täytetään alasvetolaatikot
    
    sql = """
    SELECT Nimi, ElokuvaID
    FROM Elokuva
    """
    
    teeKysely(sql, "Ei löydy elokuva", cur)
    
    for row in cur.fetchall():
        elokuvat.append(dict(elokuva=row['Nimi'].decode("UTF-8"),eid=row['ElokuvaID']))
        
    sql = """
    SELECT Nimi, JasenID
    FROM Jasen
    """
    
    teeKysely(sql, "Ei löydy jasenta", cur)
  
    for row in cur.fetchall():
        jasenet.append(dict(jasen=row['Nimi'].decode("UTF-8"), jid=row['JasenID']))
    

    con.close()
    return render_template('uusivuokraus.html', elokuvat=elokuvat,jasenet=jasenet,
    virhe=virhe).encode("UTF-8")

    
@app.route('/kirjaudu', methods=['POST','GET']) 
def kirjaudu():
    t = hashlib.sha512()
    s = hashlib.sha512()
    
    try:
        tunnus=request.form['tunnus']
    except:
        tunnus=""
    
    
    try:
        salasana=request.form['salasana']
    except:
        salasana=""
        
    try:
        submit=request.form['laheta'].decode("UTF-8")
    except:
        submit=""
    
    avain = "salainenavain"
    #m.update(avain)
    #m.update(salasana)
    
    t.update(avain)
    t.update(tunnus)
    
    s.update(avain)
    s.update(salasana)
    
    
    
    if t.digest()=="\xbb\xdfql\xf3\xf9\x1c\x11 \x0cY\x1a\x9a\x7fdn\xd1\xdb\xa3e|\xc5R\x06\xbd\x80\xd3\xff\x16\x07z\xe6\xd2F\xcb\xbaL\xf7\xa2\x19{\xc6\x8d\xb2\x92\x13\x19i\x9bj=\x95\x82fE\xf3)/q\xb1\xb6B\x9e\x1f" and \
       s.digest() == "=5Q\x0fz\x04\x98\x01/\xb7e\x80J\xfar'g\xe9\x11\xfc\xac\\W\xec%O\x9ex\x92\\s\xc8w\x87\xa5\x9e\xa9z\x9e\xd4Gh\x91s\x93\xf3)2lN\xc8\x80\xb6,\xad\x01\x1c\xc5\xddI\xcc\xda\xa8\xbb":
        # jos kaikki ok niin asetetaan sessioon tieto kirjautumisesta ja ohjataan etusivulle
        session['kirjautunut'] = "ok"
        return redirect(url_for('etusivu'))
    # jos ei ollut oikea salasana niin pysytään kirjautumissivulla.
    
    if submit=="Kirjaudu" and t.digest()!="\xbb\xdfql\xf3\xf9\x1c\x11 \x0cY\x1a\x9a\x7fdn\xd1\xdb\xa3e|\xc5R\x06\xbd\x80\xd3\xff\x16\x07z\xe6\xd2F\xcb\xbaL\xf7\xa2\x19{\xc6\x8d\xb2\x92\x13\x19i\x9bj=\x95\x82fE\xf3)/q\xb1\xb6B\x9e\x1f":
        flash(u"Tunnusta ei löydy", 'tError')
        
    if submit=="Kirjaudu" and s.digest()!="=5Q\x0fz\x04\x98\x01/\xb7e\x80J\xfar'g\xe9\x11\xfc\xac\\W\xec%O\x9ex\x92\\s\xc8w\x87\xa5\x9e\xa9z\x9e\xd4Gh\x91s\x93\xf3)2lN\xc8\x80\xb6,\xad\x01\x1c\xc5\xddI\xcc\xda\xa8\xbb":
        flash(u"Väärä salasana", 'sError')
        

    return render_template('kirjaudu.html')
    

#Käsittelee uuden elokuvan   
@app.route('/muokkaaelokuvaa', methods=['POST','GET']) 
@auth
def muokkaaelokuvaa():
    con=connect()
    cur = con.cursor()
    
    lajityypit=[]

    virhe=""
    
    tayttoVirhe=False
    
    try:
        eid=int(request.args.get('eid'))
    except:
        eid=""
        
    try:
        eloid=int(request.form['eid']) # tämä saadaan kun on painettu submit
    except:
        eloid=""
        
    if eid=="":
        eid=eloid
    
    try:
        submit=request.form['laheta'].decode("UTF-8")
    except:
        submit=""
    
    try:
        lajityyppiID=int(request.form['lajityyppi'])
    except:
        lajityyppiID=0
        
    try: 
        nimi=request.form['nimi'].decode("utf-8")
    except:
        nimi=""
        
    try: 
        julkaisuvuosi=int(request.form['julkaisuvuosi'].decode("utf-8"))
    except:
        julkaisuvuosi=""
   
    try: 
        vuokrahinta=float(request.form['vuokrahinta'].decode("utf-8"))
    except:
        vuokrahinta=""
    
    try: 
        arvio=int(request.form['arvio'].decode("utf-8"))
    except:
        arvio=""
    # Tarkastetaan onko kentät täytetty
    if nimi=="" or julkaisuvuosi=="" or vuokrahinta=="" or arvio=="":
        tayttoVirhe=True
        
    # Poistaa elokuvan jos voi
    if submit=="Poista elokuva":
        if voikoPoistaaElokuvan(eid,cur): 
            sql = """
            DELETE FROM Elokuva WHERE ElokuvaID = :eid
            """
            try: 
                cur.execute(sql, {"eid":eid})
                con.commit()
                con.close()
                return redirect(url_for('elokuvat')) # palataan elokuvasivulle
            except:
                logging.debug("Poisto ei onnistunut")
                logging.debug(sys.exc_info()[0])
        else:
            virhe="Ei voi poistaa, elokuvalla on vuokrauksia".decode("utf-8")
    
    sql = """
    SELECT Nimi
    FROM Elokuva
    WHERE ElokuvaID= :eid
    """
    elokuvanNimi=""
    
    try:
        cur.execute(sql, {"eid":eid})
        for row in cur.fetchall():
            elokuvanNimi=row['Nimi'].decode("UTF-8")
    except:
        logging.debug("ei löytynyt elokuvaa")
        logging.debug(sys.exc_info()[0])
    
    
    # Jos ei olla ensimmäistä kertaa tulossa sivulle
    # ja vuokrapäivämäärä on väärin annetaan virhe.
    # Miten saa session katoamaan, jos käyttää "edellinen nappia"??
  
    if submit=="Muokkaa elokuvaa" and tayttoVirhe:
        virhe="Täytä kaikki kentät!".decode("utf-8")
   
    # vaihe 3!!!!
    
    # Elokuvan lisääminen
    if not tayttoVirhe and submit=="Muokkaa elokuvaa":
        sql = """
        UPDATE Elokuva SET nimi=:nimi,julkaisuvuosi=:julkaisuvuosi,
        vuokrahinta=:vuokrahinta,arvio=:arvio,lajityyppiid=:LajityyppiID 
        WHERE ElokuvaID=:eid
        """
        try:
            cur.execute(sql, {"nimi":nimi,"julkaisuvuosi":julkaisuvuosi,"vuokrahinta":vuokrahinta, 
            "arvio":arvio,"LajityyppiID":lajityyppiID, "eid":eid})
            con.commit()
            con.close()
            
            return redirect(url_for('elokuvat')) # palataan elokuvasivulle
        except:
            logging.debug("ei mennyt elokuva")
            logging.debug(sys.exc_info()[0])
    
    
    #Kyselyt joilla täytetään alasvetolaatikot
    
    sql = """
    SELECT Tyypinnimi as lajityyppi, LajityyppiID as lajiID
    FROM Lajityyppi
    """
    
    teeKysely(sql, "Ei löydy lajityyppia", cur)
    
    for row in cur.fetchall():
        lajityypit.append(dict(lajityyppi=row['lajityyppi'].decode("UTF-8"),lajiID=row['lajiID']))
        
 
    con.close()
    return render_template('muokkaaelokuvaa.html', lajityypit=lajityypit, virhe=virhe, 
    eid=eid, elokuvanNimi=elokuvanNimi).encode("UTF-8")

    

if __name__ == '__main__':
    app.debug = True
    app.run(debug=True)