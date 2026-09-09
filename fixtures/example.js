export function fetchUser(id) {
    const url = `/users/${id}`;
    return fetch(url);
}

const formatName = (first, last) => {
    return `${first} ${last}`;
};

const doubleValue = (value) => value * 2;

class Cart {
    constructor(items = []) {
        this.items = items;
    }

    get total() {
        return this.items.reduce((sum, item) => sum + item.price, 0);
    }

    addItem(item) {
        this.items.push(item);
    }

    async save() {
        return Promise.resolve(this.items);
    }
}

// function hiddenComment() { return false; }
function fake() {
    const text = "function hiddenString() { }";
    return text;
}
