function process(x) {
    if (x > 0) {
        if (x < 10) {
            if (x % 2 === 0) {
                if (x !== 4) {
                    console.log(x);
                }
            }
        }
    }
}

// Security issues
function unsafeRedirect(url) {
    window.location.href = url;  // SEC: open redirect
}

function executeCode(code) {
    return eval(code);  // SEC: eval usage
}

// XSS vulnerability
function renderUserData(user) {
    document.getElementById('user').innerHTML = user.name;  // SEC: XSS
}

// Complex function with too many nested conditions
function calculateDiscount(customer, product, qty, season, coupon, tax, shipping) {
    let discount = 0;
    if (customer.isVip) {
        if (season === "summer") {
            if (coupon) {
                if (qty > 10) {
                    if (tax < 0.2) {
                        if (shipping === "free") {
                            discount = 15;
                        } else {
                            discount = 10;
                        }
                    } else {
                        discount = 5;
                    }
                } else {
                    discount = 3;
                }
            } else {
                discount = 2;
            }
        } else {
            discount = 1;
        }
    } else {
        discount = 0;
    }
    return discount;
}

// Unused function
function unusedHelper() {
    return "This function is never called";
}