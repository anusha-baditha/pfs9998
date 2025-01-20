from flask import Flask,request,redirect,render_template,url_for,flash,session
from otp import genotp
from stoken import encode,decode
from cmail import sendmail
import os
import re
import razorpay
from mysql.connector import (connection)
mydb=connection.MySQLConnection(user='root',host='localhost',password='admin',db='ecommi')
app=Flask(__name__)
app.config['SESSION_TYPE']='filesystem'
app.secret_key='code@123'
RAZORPAY_KEY_ID='rzp_test_BdYxoi5GaEITjc'
RAZORPAY_KEY_SECRET='H0FUH2n4747ZSYBRyCn2D6rc'
client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/index')
def index():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items')
        items_data=cursor.fetchall() # retriving all the items from items table
    except Exception as e:
        print(e)
        flash('could not fetch items')
        return redirect(url_for('home'))
    else:
        return render_template('index.html',items_data=items_data)
@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        print(request.form)
        aname=request.form['username'] #anusha
        aemail=request.form['email'] #anusha@codegnan.com
        password=request.form['password'] #123
        address=request.form['address'] #my address
        status_accept=request.form['agree'] #aggred to trems (on)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(email) from admincreate where email=%s',[aemail])
        email_count=cursor.fetchone()
        if email_count[0]==0:
            otp=genotp()
            admindata={'aname':aname,'aemail':aemail,'password':password,'address':address,'accept':status_accept,'aotp':otp}
            subject='Ecommerce verification mail'
            body=f'Eommerces Verification otp for admin registration {otp}'
            sendmail(to=aemail,subject=subject,body=body)
            flash('Otp has sent given mail')
            return redirect(url_for('otp',padata=encode(data=admindata))) #encode otp
        elif email_count[0]==1:
            flash('Email Already registered pls check')
            return redirect(url_for('adminlogin'))
    return render_template('admincreate.html')
@app.route('/otp/<padata>',methods=['GET','POST'])
def otp(padata):
    if request.method=='POST':
        fotp=request.form['otp'] #user given otp
        try:
            d_data=decode(data=padata) # decoding the tokenised data {'aname':aname,'aemail':aemail,'password':password,'address':address,'accept':status_accept,'aotp':otp}
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('admincreate'))
        else:
            if d_data['aotp']==fotp: # comparing the fotp with genrated otp.
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into admincreate(email,username,password,address,accept) values(%s,%s,%s,%s,%s)',[d_data['aemail'],d_data['aname'],d_data['password'],d_data['address'],d_data['accept']])
                mydb.commit()
                cursor.close()
                flash('Registration successfull')
                return redirect(url_for('adminlogin'))
            else:
                flash('wrong otp pls try agin')
                return redirect(url_for('admincreate'))
    return render_template('adminotp.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if not session.get('admin'):
        if request.method=='POST':
            login_email=request.form['email']
            login_password=request.form['password']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(email) from admincreate where email=%s',[login_email])
                stored_emailcount=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('Connection Error')
                return redirect(url_for('adminlogin'))
            else:
                if stored_emailcount[0]==1:
                    cursor.execute('select password from admincreate where email=%s',[login_email])
                    stored_password=cursor.fetchone()
                    if login_password==stored_password[0].decode('utf-8'):
                        print(session) #before session created
                        session['admin']=login_email
                        if not session.get(login_email):
                            session[login_email]={}
                        print(session) #after session create.
                        return redirect(url_for('adminpanel'))
                    else:
                        flash('password was wrong')
                        return redirect(url_for('adminlogin'))
                else:
                    flash('Email was wrong')
                    return redirect(url_for('adminlogin'))
        return render_template('adminlogin.html')
    else:
        return redirect(url_for('adminpanel'))
@app.route('/adminpanel')
def adminpanel():
    if session.get('admin'):
        return render_template('adminpanel.html')
    else:
        return redirect(url_for('adminlogin'))
@app.route('/adminlogout')
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('adminlogin'))
    return redirect(url_for('adminlogin'))
@app.route('/adminforgot',methods=['GET','POST'])
def adminforgot():
    if request.method=='POST':
        forgot_email=request.form['email']  #accepting user email
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(email) from admincreate where email=%s',[forgot_email])
        stored_email=cursor.fetchone()
        if stored_email[0]==1:
            subject='Admin reset link for ecommy application'
            body=f"Click on the link for update password: {url_for('ad_password_update',token=encode(data=forgot_email),_external=True)}"
            sendmail(to=forgot_email,subject=subject,body=body)
            flash(f'Reset link has sent to given {forgot_email}')
            return redirect(url_for('adminforgot'))
        elif stored_email[0]==0:
            flash('NO email registred pls check')
            return redirect(url_for('adminlogin'))
    return render_template('forgot.html')
@app.route('/ad_password_upadte/<token>',methods=['GET','POST'])
def ad_password_update(token):
    if request.method=='POST':
        try:
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            dtoken=decode(data=token) # detoken the encrpt email
        except Exception as e:
            print(e)
            flash('Something went wrong')
            return redirect(url_for('adminlogin'))
        else:
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admincreate set password=%s where email=%s',[npassword,dtoken])
                mydb.commit()
                flash('password updated successfully')
                return redirect(url_for('adminlogin'))
            else:
                flash('password mismatch')
                return redirect(url_for('ad_password_update',token=token))
    return render_template('newpassword.html')
@app.route('/additem',methods=['GET','POST'])
def additem():
    if session.get('admin'):
        if request.method=='POST':
            title=request.form['title']
            desc=request.form['Discription']
            price=request.form['price']
            category=request.form['category']
            quantity=request.form['quantity']
            img_file=request.files['file']
            print(img_file.filename.split('.'))
            img_name=genotp()+'.'+img_file.filename.split('.')[-1] #create filename using user extension
            '''to store the img in static folder we need to get the path without system varies'''
            drname=os.path.dirname(os.path.abspath(__file__)) #D:\pfs7\ecommy
            static_path=os.path.join(drname,'static') #D:\pfs7\ecommy\static
            img_file.save(os.path.join(static_path,img_name))
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into items(item_id,item_name,description,price,quantity,category,image_name,added_by) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[title,desc,price,quantity,category,img_name,session.get('admin')])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Connection Error')
                return redirect(url_for('additem'))
            else:
                flash(f'{title[:10]}.. added successfully')
                return redirect(url_for('additem'))

        return render_template('additem.html')
    else:
        return redirect(url_for('adminlogin'))
@app.route('/viewallitems')
def viewallitems():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,image_name from items where added_by=%s',[session.get('admin')])
            stored_items=cursor.fetchall()
        except Exception as e:
            print(e)
            flash('connection problem')
            return redirect(url_for('adminpanel'))
        else:
            return render_template('viewall_items.html',stored_items=stored_items)
    else:
        return redirect(url_for('adminlogin'))
@app.route('/deleteitem/<item_id>')
def deleteitem(item_id):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select image_name from items where item_id=uuid_to_bin(%s)',[item_id])
        stored_image=cursor.fetchone()
        print(stored_image)
        drname=os.path.dirname(os.path.abspath(__file__)) #D:\pfs7\ecommy
        static_path=os.path.join(drname,'static')
        if stored_image[0] in os.listdir(static_path):
            os.remove(os.path.join(static_path,stored_image[0]))
        cursor.execute('delete from items where item_id=uuid_to_bin(%s)',[item_id])
        mydb.commit()
        cursor.close()
    except Exception as e:
        print(e)
        flash("couldn't delete item ")
        return redirect(url_for('viewallitems'))
    else:
        flash('item deleted successfully')
        return redirect(url_for('viewallitems'))
@app.route('/viewitem/<item_id>')
def viewitem(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=-True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('Connection error')
            return redirect(url_for('viewallitems'))
        else:
            return render_template('view_item.html',item_data=item_data)
    else:
        return redirect(url_for('adminlogin'))
@app.route('/updateitem/<item_id>',methods=['GET','POST'])
def updateitem(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=-True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone() #(item_id,item,_name)
        except Exception as e:
            print(e)
            flash('Connection error')
            return redirect(url_for('viewallitems'))
        else:
            if request.method=='POST':
                title=request.form['title']
                desc=request.form['Discription']
                price=request.form['price']
                category=request.form['category']
                quantity=request.form['quantity']
                img_file=request.files['file'] #''
                filename=img_file.filename #fetch the filename
                print(img_file,11)
                if filename=='':
                    img_name=item_data[6]  #updating with old name
                else:
                    img_name=genotp()+'.'+filename.split('.')[-1] #creating new filename if new image is uploaded
                    drname=os.path.dirname(os.path.abspath(__file__)) #D:\pfs7\ecommy
                    static_path=os.path.join(drname,'static')
                    if item_data[6] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,item_data[6]))
                    img_file.save(os.path.join(static_path,img_name))
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update items set item_name=%s,description=%s,price=%s,quantity=%s,category=%s,image_name=%s where item_id=uuid_to_bin(%s)',[title,desc,price,quantity,category,img_name,item_id])
                mydb.commit()
                cursor.close()
                flash('Item Updated successfully')
                return redirect(url_for('viewitem',item_id=item_id))                
            return render_template('update_item.html',data=item_data)        
    else:
        return redirect(url_for('adminlogin'))
@app.route('/adminupdate',methods=['GET','POST'])
def adminupdate():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select username,address,dp_image from admincreate where email=%s',[session.get('admin')])
            admin_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('Connection error')
            return redirect(url_for('adminpanel'))
        else:
            if request.method=='POST':
                username=request.form['adminname']
                address=request.form['address']
                img_data=request.files['file']
                filename=img_data.filename
                print(filename,234)
                if filename=='':
                    img_name=admin_data[2] # updating old filename if no img uploaded
                else:
                    img_name=genotp()+'.'+filename.split('.')[-1] # creating new filename
                    drname=os.path.dirname(os.path.abspath(__file__)) #D:\pfs7\ecommy
                    static_path=os.path.join(drname,'static')
                    if admin_data[2] in os.listdir(static_path): #if oldimg exists in staticfolder
                        os.remove(os.path.join(static_path,admin_data[2]))
                    img_data.save(os.path.join(static_path,img_name)) # saving new file in static
                cursor.execute('update admincreate set username=%s,address=%s,dp_image=%s where email=%s',[username,address,img_name,session.get('admin')])
                mydb.commit()
                cursor.close()
                flash('profile updated successfully')
                return redirect(url_for('adminupdate'))

            return render_template('adminupdate.html',admin_data=admin_data)
    else:
        return redirect(url_for('adminlogin'))

#user login system
@app.route('/usercreate',methods=['GET','POST'])
def usercreate():
    if request.method=='POST':
        print(request.form)
        uname=request.form['name'] #anusha
        uemail=request.form['email'] #anusha@codegnan.com
        password=request.form['password'] #123
        address=request.form['address'] #my address
        gender=request.form['usergender'] #aggred to trems (on)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(user_email) from usercreate where user_email=%s',[uemail])
        email_count=cursor.fetchone()
        if email_count[0]==0:
            otp=genotp()
            userdata={'uname':uname,'uemail':uemail,'password':password,'address':address,'gender':gender,'uotp':otp}
            subject='Ecommerce verification mail'
            body=f'Eommerces Verification otp for user registration {otp}'
            sendmail(to=uemail,subject=subject,body=body)
            flash('Otp has sent given mail')
            return redirect(url_for('uotp',pudata=encode(data=userdata))) #encode otp
        elif email_count[0]==1:
            flash('Email Already registered pls check')
            return redirect(url_for('userlogin'))
    return render_template('usersignup.html')
@app.route('/uotp/<pudata>',methods=['GET','POST'])
def uotp(pudata):
    if request.method=='POST':
        fotp=request.form['otp'] #user given otp
        try:
            d_data=decode(data=pudata) # decoding the tokenised data 
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('usercreate'))
        else:
            if d_data['uotp']==fotp: # comparing the fotp with genrated otp.
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into usercreate(user_email,username,password,address,gender) values(%s,%s,%s,%s,%s)',[d_data['uemail'],d_data['uname'],d_data['password'],d_data['address'],d_data['gender']])
                mydb.commit()
                cursor.close()
                flash('Registration successfull')
                return redirect(url_for('userlogin'))
            else:
                flash('wrong otp pls try agin')
                return redirect(url_for('usercreate'))
    return render_template('userotp.html')
@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if not session.get('user'):
        if request.method=='POST':
            login_email=request.form['email']
            login_password=request.form['password']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(user_email) from usercreate where user_email=%s',[login_email])
                stored_emailcount=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('Connection Error')
                return redirect(url_for('userlogin'))
            else:
                if stored_emailcount[0]==1:
                    cursor.execute('select password from usercreate where user_email=%s',[login_email])
                    stored_password=cursor.fetchone()
                    if login_password==stored_password[0].decode('utf-8'):
                        print(session) #before session created
                        session['user']=login_email
                        if not session.get(login_email):
                            session[login_email]={}
                        print(session) #after session create.
                        return redirect(url_for('index'))
                    else:
                        flash('password was wrong')
                        return redirect(url_for('userlogin'))
                else:
                    flash('Email was wrong')
                    return redirect(url_for('userlogin'))
        return render_template('userlogin.html')
    else:
        return redirect(url_for('index'))
@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('userlogin'))
    return redirect(url_for('userlogin'))
@app.route('/category/<type>')
def category(type):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items where category=%s',[type])
        items_data=cursor.fetchall() # retriving all the items from items table
    except Exception as e:
        print(e)
        flash('could not fetch items')
        return redirect(url_for('index'))
    return render_template('dashboard.html',items_data=items_data)
@app.route('/addcart/<itemid>/<name>/<float:price>/<qyt>/<image>/<category>')
def addcart(itemid,name,price,qyt,image,category):
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        print(session) #{}
        if itemid not in session['user']:
            session[session.get('user')][itemid]=[name,price,1,image,category,qyt]
            session.modified=True
            print(session)
            flash(f'{name} added to cart')
            return redirect(url_for('index'))
        session[session.get('user')][itemid][2]+=1
        flash('item already in cart')
        return redirect(url_for('index'))
@app.route('/viewcart')
def viewcart():
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        if session.get(session.get('user')):
            items=session[session.get('user')]
            print(items)
        else:
            items='empty'
        if items=='empty':
            flash('No products added to cart')
            return redirect(url_for('index'))
        return render_template('cart.html',items=items)
@app.route('/removecart_item/<itemid>')
def removecart_item(itemid):
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        session.get(session.get('user')).pop(itemid)
        session.modified=True
        flash('item removed from cart')
        return redirect(url_for('viewcart'))
@app.route('/description/<itemid>')
def description(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,description,quantity,price,category,image_name from items where item_id=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone() # retriving  the item from items table
    except Exception as e:
        print(e)
        flash('could not fetch items')
        return redirect(url_for('index'))
    return render_template('description.html',item_data=item_data)
@app.route('/pay/<itemid>/<name>/<float:price>',methods=['GET','POST'])
def pay(itemid,name,price):
    try:
        qyt=int(request.form['qyt'])
        amount=price*100 
        total_price=amount*qyt
        print(amount,qyt,total_price)
        print(f'Creating payment for item:{itemid},name:{name},price:{total_price}')
        #create Razorpay order
        order=client.order.create({
            'amount':total_price,
            'currency':'INR',
            'payment_capture':'1'
        })
        print(f"order created: {order}")
        return render_template('pay.html',order=order,itemid=itemid,name=name,price=total_price,qyt=qyt)
    except Exception as e:
        #Log the error and return a 400 response
        print(f'Error creating order: {str(e)}')
        flash('Error in payment')
        return redirect(url_for('index'))
@app.route('/success',methods=['POST'])
def success():
    #extract payment details from the form
    payment_id=request.form.get('razorpay_payment_id')
    order_id=request.form.get('razorpay_order_id')
    signature=request.form.get('razorpay_signature')
    name=request.form.get('name')
    itemid=request.form.get('itemid')
    price=request.form.get('total_price')
    qyt=request.form.get('qyt')
    #verification process
    params_dict={
        'razorpay_order_id':order_id,
        'razorpay_payment_id':payment_id,
        'razorpay_signature':signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into orders(itemid,item_name,total_price,user,qty) values(uuid_to_bin(%s),%s,%s,%s,%s)',[itemid,name,price,session.get('user'),qyt])
        mydb.commit()
        cursor.close()
        flash('order placed successfully')
        return 'success'
    except razorpay.errors.SignatureVerificationError:
        return 'Payment  verification failed!',400
@app.route('/orders')
def orders():
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select orderid,bin_to_uuid(itemid),item_name,total_price,user,qty from orders where user=%s',[session.get('user')])
            ordlist=cursor.fetchall()
        except Exception as e:
            print('Error in fetching orders')
            flash("Could n't fetch orders")
            return redirect(url_for('index'))
        else:
            return render_template('orders.html',ordlist=ordlist)
    return redirect(url_for('userlogin'))
@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        search=request.form['search'] # 'apple' some user may give ''
        strg=['A-Za-z0-9']
        pattern=re.compile(f'{strg}',re.IGNORECASE)
        if (pattern.match(search)):
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items where item_name like %s or price like %s or category like %s or description like %s',['%'+search+'%','%'+search+'%','%'+search+'%','%'+search+'%'])
                searcheddata=cursor.fetchall()
            except Exception as e:
                print(f'error to fetch searchdata:{e}')
                flash('could not fetch data')
                return redirect(url_for('index'))
            else:
                return render_template('dashboard.html',items_data=searcheddata)
        else:
            flash('No data given invalid search')
            return redirect(url_for('index'))
    return render_template('index.html')
@app.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            reviewtext=request.form['review']
            rating=request.form['rate']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into reviews(username,itemid,title,review,rating) values(%s,uuid_to_bin(%s),%s,%s,%s)',[session.get('user'),itemid,title,reviewtext,rating])
                mydb.commit()
            except Exception as e:
                print(f'Error in inserting review:{e}')
                flash("Can't add a review")
                return redirect(url_for('description',itemid=itemid))
            else:
                cursor.close()
                flash('review has given')
                return redirect(url_for('description',itemid=itemid))
        return render_template('review.html')
    else:
        return redirect(url_for('userlogin'))
app.run(debug=True,use_reloader=True)
