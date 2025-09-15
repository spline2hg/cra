const userInput = location.hash.slice(1);
document.body.innerHTML = userInput;

if (userInput == "admin") {
    console.log("admin");
}

function handleUser(data) {
    const html = `<div>${data.name}</div>`;
    document.body.innerHTML = html;
    console.log("user rendered");
}

// Security issue - using eval
eval("console.log('This is dangerous')");

// Duplicate code example
function processOrderA(items) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        if (items[i].category === "electronics") {
            if (items[i].price > 1000) {
                total += items[i].price * 0.8;
            } else {
                total += items[i].price * 0.9;
            }
        } else {
            total += items[i].price;
        }
    }
    return total;
}

function processOrderB(items) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        if (items[i].category === "electronics") {
            if (items[i].price > 1000) {
                total += items[i].price * 0.8;
            } else {
                total += items[i].price * 0.9;
            }
        } else {
            total += items[i].price;
        }
    }
    return total;
}

// Unused variable
function calculateTotal(price) {
    const tax = 0.08;
    const unusedVar = "This is not used";
    return price + (price * tax);
}