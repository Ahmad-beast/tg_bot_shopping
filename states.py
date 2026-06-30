from aiogram.fsm.state import State, StatesGroup


class AddProduct(StatesGroup):
    details = State()


class EditProduct(StatesGroup):
    value = State()


class AddStock(StatesGroup):
    items = State()


class Broadcast(StatesGroup):
    message = State()
    button_choice = State()
    product_select = State()
    custom_button = State()


class AddBalance(StatesGroup):
    user_id = State()
    amount = State()


class BanUser(StatesGroup):
    user_id = State()


class TopUp(StatesGroup):
    amount = State()

class ChannelPost(StatesGroup):
    message = State()

class BulkUpload(StatesGroup):
    file = State()

class UserLookup(StatesGroup):
    query = State()

class CustomBalance(StatesGroup):
    amount = State()

class AddCategory(StatesGroup):
    emoji = State()
    name = State()

class AddPromo(StatesGroup):
    code = State()
    type = State()
    value = State()
    max_uses = State()

class BuyProduct(StatesGroup):
    quantity = State()
    promo_code = State()

class SupportTicket(StatesGroup):
    message = State()

class AdminReplySupport(StatesGroup):
    message = State()

class ProductReview(StatesGroup):
    rating = State()
    comment = State()

class RedeemPromo(StatesGroup):
    code = State()
