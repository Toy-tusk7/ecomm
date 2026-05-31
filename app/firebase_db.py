import os
import json
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase admin SDK imports
use_firebase = False
db_client = None

# Locate credentials
creds_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'firebase-credentials.json'))
if os.path.exists(creds_path):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Avoid double initialization
        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)
        db_client = firestore.client()
        use_firebase = True
        logger.info("[Firebase] ✓ Successfully initialized live Firestore database")
    except Exception as e:
        logger.warning(f"[Firebase] Failed to initialize live client ({e}), falling back to local JSON")
else:
    logger.info("[Firebase] No firebase-credentials.json found, using local JSON fallback")

MOCK_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'firebase_mock.json'))

def load_mock_db():
    os.makedirs(os.path.dirname(MOCK_DB_PATH), exist_ok=True)
    if not os.path.exists(MOCK_DB_PATH):
        # Initial empty state
        return {
            "users": {},
            "categories": {},
            "products": {},
            "cart_items": {},
            "orders": {},
            "order_items": {}
        }
    try:
        with open(MOCK_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[MockDB] Error reading mock JSON file ({e})")
        return {
            "users": {},
            "categories": {},
            "products": {},
            "cart_items": {},
            "orders": {},
            "order_items": {}
        }

def save_mock_db(data):
    try:
        os.makedirs(os.path.dirname(MOCK_DB_PATH), exist_ok=True)
        with open(MOCK_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MockDB] Error writing mock JSON file ({e})")

# ─── DATABASE CORE CRUD OPERATORS ───

def get_documents(collection_name):
    if use_firebase:
        try:
            docs = db_client.collection(collection_name).stream()
            res = []
            for doc in docs:
                data = doc.to_dict()
                try:
                    data['id'] = int(doc.id)
                except ValueError:
                    data['id'] = doc.id
                res.append(data)
            return res
        except Exception as e:
            logger.error(f"[Firebase] Error listing collection {collection_name} ({e})")
            return []
    else:
        db_data = load_mock_db()
        coll = db_data.get(collection_name, {})
        res = []
        for doc_id, data in coll.items():
            doc_data = data.copy()
            try:
                doc_data['id'] = int(doc_id)
            except ValueError:
                doc_data['id'] = doc_id
            res.append(doc_data)
        return res

def get_document(collection_name, doc_id):
    if doc_id is None:
        return None
    if use_firebase:
        try:
            doc = db_client.collection(collection_name).document(str(doc_id)).get()
            if doc.exists:
                data = doc.to_dict()
                try:
                    data['id'] = int(doc.id)
                except ValueError:
                    data['id'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"[Firebase] Error reading document {doc_id} in {collection_name} ({e})")
            return None
    else:
        db_data = load_mock_db()
        coll = db_data.get(collection_name, {})
        data = coll.get(str(doc_id))
        if data:
            doc_data = data.copy()
            try:
                doc_data['id'] = int(doc_id)
            except ValueError:
                doc_data['id'] = doc_id
            return doc_data
        return None

def save_document(collection_name, doc_id, data):
    # Ensure fields like datetime are converted to ISO format strings for JSON compatibility
    clean_data = data.copy()
    for k, v in list(clean_data.items()):
        if isinstance(v, datetime):
            clean_data[k] = v.isoformat()
            
    if use_firebase:
        try:
            coll_ref = db_client.collection(collection_name)
            if doc_id is None:
                doc_ref = coll_ref.document()
                doc_id = doc_ref.id
            else:
                doc_ref = coll_ref.document(str(doc_id))
            
            # Avoid storing duplicate ID key in the document fields
            if 'id' in clean_data:
                del clean_data['id']
            doc_ref.set(clean_data)
            try:
                return int(doc_id)
            except ValueError:
                return doc_id
        except Exception as e:
            logger.error(f"[Firebase] Error saving document in {collection_name} ({e})")
            return None
    else:
        db_data = load_mock_db()
        if collection_name not in db_data:
            db_data[collection_name] = {}
        coll = db_data[collection_name]
        
        if doc_id is None:
            existing_ids = []
            for k in coll.keys():
                try:
                    existing_ids.append(int(k))
                except ValueError:
                    pass
            doc_id = max(existing_ids) + 1 if existing_ids else 1
            
        clean_data['id'] = doc_id
        coll[str(doc_id)] = clean_data
        save_mock_db(db_data)
        return doc_id

def delete_document(collection_name, doc_id):
    if doc_id is None:
        return
    if use_firebase:
        try:
            db_client.collection(collection_name).document(str(doc_id)).delete()
        except Exception as e:
            logger.error(f"[Firebase] Error deleting document {doc_id} in {collection_name} ({e})")
    else:
        db_data = load_mock_db()
        coll = db_data.get(collection_name, {})
        if str(doc_id) in coll:
            del coll[str(doc_id)]
            save_mock_db(db_data)

# ─── MODEL QUERY IMPLEMENTATION ───

class Query:
    def __init__(self, model_class):
        self.model_class = model_class
        self.filters = []
        self.sort_field = None
        self.sort_desc = False
        self.limit_num = None

    def filter_by(self, **kwargs):
        for k, v in kwargs.items():
            self.filters.append((k, '==', v))
        return self

    def filter(self, *args):
        # Mimic simple SQLAlchemy filter conditions (like Product.category_id == x)
        # We parse arguments to build query filters.
        for arg in args:
            # We assume binary expressions or tuples
            # For our cases, we can check if it contains attributes or direct operators.
            # E.g. Product.category_id == val
            # To handle filter expressions simply, we can evaluate filter attributes or pass them.
            pass
        return self

    def order_by(self, field_expr):
        # field_expr could be a string or a sort field descriptor
        # If it is like `Order.created_at.desc()`, it may have a custom string representation or wrapper
        expr_str = str(field_expr)
        if 'desc' in expr_str.lower():
            self.sort_desc = True
        else:
            self.sort_desc = False
        
        # Extract base property name
        clean_field = expr_str.split('.')[-1].replace('()', '').replace('desc', '').replace('asc', '').strip('_ ')
        # Special matching for common sort fields
        if 'created_at' in expr_str:
            self.sort_field = 'created_at'
        else:
            self.sort_field = clean_field if clean_field else None
        return self

    def limit(self, num):
        self.limit_num = num
        return self

    def get(self, doc_id):
        data = get_document(self.model_class.collection_name, doc_id)
        if data:
            return self.model_class(**data)
        return None

    def get_or_404(self, doc_id):
        obj = self.get(doc_id)
        if not obj:
            from flask import abort
            abort(404)
        return obj

    def all(self):
        docs = get_documents(self.model_class.collection_name)
        
        # Apply filters in-memory (handles both JSON and Firestore local lists)
        filtered_docs = []
        for doc in docs:
            match = True
            for field, op, val in self.filters:
                doc_val = doc.get(field)
                if op == '==':
                    if doc_val != val:
                        match = False
                        break
            if match:
                filtered_docs.append(doc)
                
        # Apply Sorting
        if self.sort_field:
            filtered_docs.sort(
                key=lambda x: x.get(self.sort_field) if x.get(self.sort_field) is not None else '',
                reverse=self.sort_desc
            )
            
        # Apply Limit
        if self.limit_num:
            filtered_docs = filtered_docs[:self.limit_num]
            
        return [self.model_class(**d) for d in filtered_docs]

    def first(self):
        res = self.all()
        return res[0] if res else None

    def count(self):
        return len(self.all())

    def __iter__(self):
        return iter(self.all())


# ─── MODELS MAPPING DEFINITIONS ───

class FieldDescriptor:
    def __init__(self, name):
        self.name = name
    def desc(self):
        return f"{self.name} desc"
    def asc(self):
        return f"{self.name} asc"
    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name

class FirebaseModelMeta(type):
    @property
    def query(cls):
        return cls.query_class(cls)

    def __getattr__(cls, name):
        if name.startswith('_'):
            raise AttributeError(f"type object '{cls.__name__}' has no attribute '{name}'")
        return FieldDescriptor(name)

class FirebaseModel(metaclass=FirebaseModelMeta):
    query_class = Query

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        # Assure ID exists
        if not hasattr(self, 'id'):
            self.id = None

    def save(self):
        # Export fields to dict
        data = {}
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                data[k] = v
        # Save to database
        new_id = save_document(self.collection_name, self.id, data)
        self.id = new_id
        return self

    def delete(self):
        if self.id is not None:
            delete_document(self.collection_name, self.id)


class User(FirebaseModel):
    collection_name = 'users'

    # Flask-Login integration properties
    @property
    def is_authenticated(self):
        return True
    @property
    def is_active(self):
        return True
    @property
    def is_anonymous(self):
        return False
    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        # Safeguard if password_hash is not set
        p_hash = getattr(self, 'password_hash', None)
        if not p_hash:
            return False
        return check_password_hash(p_hash, password)

    @property
    def cart_items(self):
        return Query(CartItem).filter_by(user_id=self.id)

    @property
    def orders(self):
        return Query(Order).filter_by(user_id=self.id)


class Category(FirebaseModel):
    collection_name = 'categories'

    @property
    def products(self):
        return Query(Product).filter_by(category_id=self.id)


class Product(FirebaseModel):
    collection_name = 'products'

    @property
    def category(self):
        return Query(Category).get(self.category_id)

    @property
    def cart_items(self):
        return Query(CartItem).filter_by(product_id=self.id)

    @property
    def order_items(self):
        return Query(OrderItem).filter_by(product_id=self.id)


class CartItem(FirebaseModel):
    collection_name = 'cart_items'

    @property
    def product(self):
        return Query(Product).get(self.product_id)

    @property
    def user(self):
        return Query(User).get(self.user_id)


class Order(FirebaseModel):
    collection_name = 'orders'

    @property
    def items(self):
        return Query(OrderItem).filter_by(order_id=self.id)

    @property
    def user(self):
        return Query(User).get(self.user_id)


class OrderItem(FirebaseModel):
    collection_name = 'order_items'

    @property
    def product(self):
        return Query(Product).get(self.product_id)

    @property
    def order(self):
        return Query(Order).get(self.order_id)
