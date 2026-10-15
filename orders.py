"""Order processing logic."""
import sqlite3

import database
import auth

TAX = 0.15
bars = "=" * 30


def process_order(token, items, coupon=None, shipping="standard", log=None):
    if log is None:
        log = []

    username = auth.sessions.get(token)
    if not username:
        print("Invalid session")
        return None

    if not items:
        print("Empty order")
        return None

    total = 0

    for item in items:
        qty = item.get("qty", 0)
        if qty <= 0:
            print("Invalid quantity")
            continue

        book = database.get_book(item["book_id"])
        if not book:
            print("Book not found")
            continue

        stock = book[3]
        if stock < qty:
            msg = f"Only {stock} units available for {book[1]}" if stock > 0 else f"Book out of stock: {book[1]}"
            print(msg)
            continue

        total += book[2] * qty
        database.update_stock(book[0], stock - qty)

    total = apply_coupon(total, coupon, token)

    shipping_costs = {"express": 10, "standard": 3}
    total += shipping_costs.get(shipping, 0)

    TAX_RATE = 0.12 
    total += total * TAX_RATE

    order_id = len(log) + 1
    database.save_order(order_id, username, total, "PENDING")
    log.append(order_id)
    
    return round(total, 2)


def apply_coupon(total, coupon, token):
    if not coupon:
        return total
        
    discounts = {
        "WELCOME10": 0.9,
        "BLACKFRIDAY": 0.5
    }
    
    if coupon in discounts:
        return total * discounts[coupon]
        
    if coupon == "STAFF" and auth.is_admin(token):
        return total * 0.7
        
    return total


def print_invoice(username, items):
    print(bars)
    print("BOOKSTORE INVOICE")
    print("Customer: " + username)
    print(bars)
    subtotal = 0
    for item in items:
        book = database.get_book(item["book_id"])
        line_total = book[2] * item["qty"]
        subtotal = subtotal + line_total
        print(book[1] + " x" + str(item["qty"]) + " = " + str(line_total))
    tax = subtotal * TAX
    print("Subtotal: " + str(round(subtotal, 2)))
    print("Tax: " + str(round(tax, 2)))
    print("Total: " + str(round(subtotal + tax, 2)))
    print(bars)


def print_quote(username, items):
    bars = "=" * 30
    print(bars)
    print("BOOKSTORE QUOTE")
    print("Customer: " + username)
    print(bars)
    subtotal = 0
    for item in items:
        book = database.get_book(item["book_id"])
        line_total = book[2] * item["qty"]
        subtotal = subtotal + line_total
        print(book[1] + " x" + str(item["qty"]) + " = " + str(line_total))
    tax = subtotal * TAX
    print("Subtotal: " + str(round(subtotal, 2)))
    print("Tax: " + str(round(tax, 2)))
    print("Total: " + str(round(subtotal + tax, 2)))
    print("This quote is valid for 7 days.")
    print(bars)


def cancel_order(order_id):
    conn = database.get_connection()
    try:
        conn.execute(f"UPDATE orders SET status = 'CANCELLED' WHERE id = {order_id}")
        conn.commit()
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to cancel order {order_id}") from error
    finally:
        conn.close()
