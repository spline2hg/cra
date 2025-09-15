def calculate_discount(customer, product, qty, season, coupon, tax, shipping):
    """Mega-function to trigger high complexity."""
    discount = 0
    if customer.is_vip:
        if season == "summer":
            if coupon:
                if qty > 10:
                    if tax < 0.2:
                        if shipping == "free":
                            discount = 15
                        else:
                            discount = 10
                    else:
                        discount = 5
                else:
                    discount = 3
            else:
                discount = 2
        else:
            discount = 1
    else:
        discount = 0
    return discount

def process_order(items):
    """Function with high cyclomatic complexity."""
    total = 0
    for item in items:
        if item.category == "electronics":
            if item.price > 1000:
                if item.brand == "premium":
                    total += item.price * 0.7
                else:
                    total += item.price * 0.8
            else:
                total += item.price * 0.9
        elif item.category == "clothing":
            total += item.price * 0.85
        else:
            total += item.price
    return total

# Unused function - dead code
def unused_helper():
    return "This function is never called"