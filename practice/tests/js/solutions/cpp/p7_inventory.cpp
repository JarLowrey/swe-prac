#include <bits/stdc++.h>
using namespace std;

class Inventory {
    struct Discount {
        int percent, start, end;
    };
    struct Product {
        int price;
        int stock = 0;
        int sold = 0; // net of returns
        vector<Discount> discounts;
    };
    struct Line {
        int qty;
        int unitPrice;
        int returned = 0;
    };

    unordered_map<string, Product> products;
    unordered_map<string, unordered_map<string, Line>> orders;
    vector<pair<int, long long>> ledger; // (timestamp, +sale or -refund)
    int nextOrder = 1;

    int unitPrice(const Product& product, int timestamp) {
        int percent = 0;
        for (const Discount& d : product.discounts) {
            if (d.start <= timestamp && timestamp < d.end) percent = max(percent, d.percent);
        }
        return (int)((long long)product.price * (100 - percent) / 100);
    }

public:
    Inventory() {
    }

    bool addProduct(int timestamp, string sku, int price) {
        return products.emplace(sku, Product{price}).second;
    }

    optional<int> restock(int timestamp, string sku, int qty) {
        auto it = products.find(sku);
        if (it == products.end() || qty <= 0) return nullopt;
        it->second.stock += qty;
        return it->second.stock;
    }

    optional<string> sell(int timestamp, string sku, int qty) {
        return placeOrder(timestamp, {{sku, qty}});
    }

    optional<string> placeOrder(int timestamp, const vector<pair<string, int>>& lines) {
        if (lines.empty()) return nullopt;
        vector<pair<string, int>> wanted; // merged by sku, in first-seen order
        unordered_map<string, size_t> at;
        for (const auto& [sku, qty] : lines) {
            if (!products.count(sku) || qty <= 0) return nullopt;
            auto [it, added] = at.emplace(sku, wanted.size());
            if (added) {
                wanted.emplace_back(sku, qty);
            } else {
                wanted[it->second].second += qty;
            }
        }
        for (const auto& [sku, qty] : wanted) {
            if (products[sku].stock < qty) return nullopt;
        }
        string orderId = "order" + to_string(nextOrder++);
        auto& order = orders[orderId];
        for (const auto& [sku, qty] : wanted) {
            Product& product = products[sku];
            int unit = unitPrice(product, timestamp);
            product.stock -= qty;
            product.sold += qty;
            order[sku] = Line{qty, unit};
            ledger.emplace_back(timestamp, (long long)unit * qty);
        }
        return orderId;
    }

    string topSellers(int timestamp, int n) {
        vector<pair<string, int>> ranked;
        for (const auto& [sku, product] : products) {
            if (product.sold > 0) ranked.emplace_back(sku, product.sold);
        }
        sort(ranked.begin(), ranked.end(), [](const pair<string, int>& a, const pair<string, int>& b) {
            return a.second != b.second ? a.second > b.second : a.first < b.first;
        });
        string out;
        for (int i = 0; i < min<int>(n, ranked.size()); i++) {
            if (i) out += ", ";
            out += ranked[i].first + "(" + to_string(ranked[i].second) + ")";
        }
        return out;
    }

    bool setPrice(int timestamp, string sku, int price) {
        auto it = products.find(sku);
        if (it == products.end()) return false;
        it->second.price = price;
        return true;
    }

    optional<int> returnItems(int timestamp, string orderId, string sku, int qty) {
        auto order = orders.find(orderId);
        if (order == orders.end()) return nullopt;
        auto found = order->second.find(sku);
        if (found == order->second.end()) return nullopt;
        Line& line = found->second;
        if (qty <= 0 || qty > line.qty - line.returned) return nullopt;
        line.returned += qty;
        Product& product = products[sku];
        product.stock += qty;
        product.sold -= qty;
        int refund = qty * line.unitPrice;
        ledger.emplace_back(timestamp, -refund);
        return refund;
    }

    bool addDiscount(int timestamp, string sku, int percent, int startTs, int endTs) {
        auto it = products.find(sku);
        if (it == products.end()) return false;
        it->second.discounts.push_back({percent, startTs, endTs});
        return true;
    }

    int revenue(int timestamp, int startTs, int endTs) {
        long long total = 0;
        for (const auto& [ts, amount] : ledger) {
            if (startTs <= ts && ts < endTs) total += amount;
        }
        return (int)total;
    }
};
