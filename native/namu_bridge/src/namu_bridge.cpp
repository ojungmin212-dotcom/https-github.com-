#include <windows.h>

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

const DWORD CA_WMCAEVENT = WM_USER + 8400;
const DWORD CA_CONNECTED = WM_USER + 110;
const DWORD CA_DISCONNECTED = WM_USER + 120;
const DWORD CA_SOCKETERROR = WM_USER + 130;
const DWORD CA_RECEIVEDATA = WM_USER + 210;
const DWORD CA_RECEIVEMESSAGE = WM_USER + 230;
const DWORD CA_RECEIVECOMPLETE = WM_USER + 240;
const DWORD CA_RECEIVEERROR = WM_USER + 250;

const int TRID_QUOTE = 1;
const int TRID_BUY_ORDER = 2;
const int TRID_SELL_ORDER = 3;

typedef BOOL(__stdcall TLoad)();
typedef BOOL(__stdcall TFree)();
typedef BOOL(__stdcall TConnect)(HWND, DWORD, char, char, const char*, const char*, const char*);
typedef BOOL(__stdcall TDisconnect)();
typedef BOOL(__stdcall TQuery)(HWND, int, const char*, const char*, int, int);

typedef struct {
    char* szBlockName;
    char* szData;
    int nLen;
} RECEIVED;

typedef struct {
    int TrIndex;
    RECEIVED* pData;
} OUTDATABLOCK;

typedef struct {
    char form_lang[1];
    char _form_lang;
    char shrn_iscd[6];
    char _shrn_iscd;
} TIVWUTKMST04In;

typedef struct {
    char shrn_iscd[6];
    char _shrn_iscd;
    char hts_isnm[41];
    char _hts_isnm;
    char stck_prpr[10];
    char _stck_prpr;
} TIVWUTKMST04Out1;

struct AppState {
    bool connected = false;
    bool done = false;
    bool query_complete = false;
    int price = 0;
    std::string error;
};

static AppState g_state;

std::string env_value(const char* name) {
    char* value = nullptr;
    size_t len = 0;
    if (_dupenv_s(&value, &len, name) != 0 || value == nullptr) {
        return "";
    }
    std::string result(value);
    free(value);
    return result;
}

std::string json_get(const std::string& raw, const std::string& key) {
    const std::string marker = "\"" + key + "\"";
    size_t pos = raw.find(marker);
    if (pos == std::string::npos) {
        return "";
    }
    pos = raw.find(':', pos);
    if (pos == std::string::npos) {
        return "";
    }
    pos++;
    while (pos < raw.size() && std::isspace(static_cast<unsigned char>(raw[pos]))) {
        pos++;
    }
    if (pos >= raw.size()) {
        return "";
    }
    if (raw[pos] == '"') {
        size_t end = raw.find('"', pos + 1);
        return end == std::string::npos ? "" : raw.substr(pos + 1, end - pos - 1);
    }
    size_t end = pos;
    while (end < raw.size() && raw[end] != ',' && raw[end] != '}') {
        end++;
    }
    return raw.substr(pos, end - pos);
}

std::string json_escape(const std::string& value) {
    std::string out;
    for (char c : value) {
        if (c == '\\' || c == '"') {
            out.push_back('\\');
        }
        if (c == '\r' || c == '\n') {
            out.push_back(' ');
        } else {
            out.push_back(c);
        }
    }
    return out;
}

bool env_yes(const char* name) {
    std::string value = env_value(name);
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return value == "YES" || value == "Y" || value == "TRUE" || value == "1";
}

std::string required_env_state() {
    std::string missing;
    if (env_value("APIF_NAMU_ACCOUNT_PASSWORD").empty()) {
        missing += missing.empty() ? "APIF_NAMU_ACCOUNT_PASSWORD" : ", APIF_NAMU_ACCOUNT_PASSWORD";
    }
    if (env_value("APIF_NAMU_ORDER_PASSWORD_1").empty()) {
        missing += missing.empty() ? "APIF_NAMU_ORDER_PASSWORD_1" : ", APIF_NAMU_ORDER_PASSWORD_1";
    }
    if (env_value("APIF_NAMU_ORDER_PASSWORD_2").empty()) {
        missing += missing.empty() ? "APIF_NAMU_ORDER_PASSWORD_2" : ", APIF_NAMU_ORDER_PASSWORD_2";
    }
    return missing;
}

std::string order_tr_code(const std::string& side) {
    if (side == "BUY") {
        return "c8102";
    }
    if (side == "SELL") {
        return "c8101";
    }
    throw std::runtime_error("side must be BUY or SELL.");
}

std::string order_tr_name(const std::string& side) {
    return side == "BUY" ? "stock buy order" : "stock sell order";
}

void send_ok(const std::string& data_json) {
    std::cout << "{\"ok\":true,\"data\":" << data_json << "}" << std::endl;
}

void send_error(const std::string& message) {
    std::cout << "{\"ok\":false,\"error\":\"" << json_escape(message) << "\"}" << std::endl;
}

void smove(char* target, size_t size, const std::string& source) {
    memset(target, ' ', size);
    memcpy(target, source.data(), min(size, source.size()));
}

int parse_numeric_field(const char* data, size_t size) {
    std::string value(data, size);
    value.erase(std::remove_if(value.begin(), value.end(), [](char c) {
        return c == ' ' || c == ',';
    }), value.end());
    if (value.empty()) {
        return 0;
    }
    return std::atoi(value.c_str());
}

LRESULT CALLBACK window_proc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    if (msg != CA_WMCAEVENT) {
        return DefWindowProc(hwnd, msg, wparam, lparam);
    }

    switch (wparam) {
    case CA_CONNECTED:
        g_state.connected = true;
        break;
    case CA_DISCONNECTED:
        g_state.error = "Disconnected from WMCA.";
        g_state.done = true;
        break;
    case CA_SOCKETERROR:
        g_state.error = "WMCA socket error.";
        g_state.done = true;
        break;
    case CA_RECEIVEDATA: {
        OUTDATABLOCK* block = reinterpret_cast<OUTDATABLOCK*>(lparam);
        if (block && block->TrIndex == TRID_QUOTE && block->pData &&
            strcmp(block->pData->szBlockName, "IVWUTKMST04Out1") == 0) {
            TIVWUTKMST04Out1* quote =
                reinterpret_cast<TIVWUTKMST04Out1*>(block->pData->szData);
            g_state.price = parse_numeric_field(quote->stck_prpr, sizeof quote->stck_prpr);
        }
        break;
    }
    case CA_RECEIVEMESSAGE:
        break;
    case CA_RECEIVECOMPLETE:
        g_state.query_complete = true;
        g_state.done = true;
        break;
    case CA_RECEIVEERROR:
        g_state.error = "WMCA query error.";
        g_state.done = true;
        break;
    default:
        break;
    }
    return TRUE;
}

HWND create_message_window() {
    WNDCLASSA wc = {};
    wc.lpfnWndProc = window_proc;
    wc.hInstance = GetModuleHandle(nullptr);
    wc.lpszClassName = "ApifNamuBridgeWindow";
    RegisterClassA(&wc);
    return CreateWindowA(
        wc.lpszClassName,
        "APIF Namu Bridge",
        0,
        0,
        0,
        0,
        0,
        HWND_MESSAGE,
        nullptr,
        wc.hInstance,
        nullptr);
}

bool wait_until(bool (*predicate)(), int timeout_ms) {
    auto start = std::chrono::steady_clock::now();
    MSG msg;
    while (!predicate()) {
        while (PeekMessage(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
        if (std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - start)
                .count() > timeout_ms) {
            return false;
        }
        Sleep(10);
    }
    return true;
}

bool is_connected() {
    return g_state.connected || !g_state.error.empty();
}

bool is_done() {
    return g_state.done;
}

class WmcaClient {
public:
    WmcaClient() {
        std::string root = env_value("APIF_NAMU_QV_PATH");
        if (root.empty()) {
            throw std::runtime_error("APIF_NAMU_QV_PATH is empty.");
        }
        std::string bin = root + "\\bin";
        SetDllDirectoryA(bin.c_str());
        dll_ = LoadLibraryA((bin + "\\wmca.dll").c_str());
        if (!dll_) {
            throw std::runtime_error("Failed to load wmca.dll.");
        }
        load_ = reinterpret_cast<TLoad*>(GetProcAddress(dll_, "wmcaLoad"));
        free_ = reinterpret_cast<TFree*>(GetProcAddress(dll_, "wmcaFree"));
        connect_ = reinterpret_cast<TConnect*>(GetProcAddress(dll_, "wmcaConnect"));
        disconnect_ = reinterpret_cast<TDisconnect*>(GetProcAddress(dll_, "wmcaDisconnect"));
        query_ = reinterpret_cast<TQuery*>(GetProcAddress(dll_, "wmcaQuery"));
        if (!load_ || !free_ || !connect_ || !disconnect_ || !query_) {
            throw std::runtime_error("Required WMCA functions were not found.");
        }
        if (!load_()) {
            throw std::runtime_error("wmcaLoad failed.");
        }
    }

    ~WmcaClient() {
        if (disconnect_) {
            disconnect_();
        }
        if (free_) {
            free_();
        }
        if (dll_) {
            FreeLibrary(dll_);
        }
    }

    void connect(HWND hwnd) {
        std::string id = env_value("APIF_NAMU_USER_ID");
        std::string password = env_value("APIF_NAMU_USER_PASSWORD");
        std::string cert_password = env_value("APIF_NAMU_CERT_PASSWORD");
        if (id.empty() || password.empty()) {
            throw std::runtime_error("APIF_NAMU_USER_ID or APIF_NAMU_USER_PASSWORD is empty.");
        }
        if (!connect_(hwnd, CA_WMCAEVENT, 'T', 'W', id.c_str(), password.c_str(), cert_password.c_str())) {
            throw std::runtime_error("wmcaConnect failed.");
        }
        if (!wait_until(is_connected, 30000) || !g_state.connected) {
            throw std::runtime_error(g_state.error.empty() ? "WMCA login timeout." : g_state.error);
        }
    }

    int quote(HWND hwnd, const std::string& symbol) {
        TIVWUTKMST04In input;
        memset(&input, 0x20, sizeof input);
        smove(input.form_lang, sizeof input.form_lang, "k");
        smove(input.shrn_iscd, sizeof input.shrn_iscd, symbol);

        g_state.done = false;
        g_state.query_complete = false;
        g_state.price = 0;
        g_state.error.clear();

        if (!query_(hwnd, TRID_QUOTE, "IVWUTKMST04.UNT", reinterpret_cast<const char*>(&input), sizeof input, 0)) {
            throw std::runtime_error("wmcaQuery quote failed.");
        }
        if (!wait_until(is_done, 30000)) {
            throw std::runtime_error("Quote query timeout.");
        }
        if (!g_state.error.empty()) {
            throw std::runtime_error(g_state.error);
        }
        if (g_state.price <= 0) {
            throw std::runtime_error("Quote response did not include a valid price.");
        }
        return g_state.price;
    }

private:
    HMODULE dll_ = nullptr;
    TLoad* load_ = nullptr;
    TFree* free_ = nullptr;
    TConnect* connect_ = nullptr;
    TDisconnect* disconnect_ = nullptr;
    TQuery* query_ = nullptr;
};

int main() {
    try {
        std::string raw;
        std::getline(std::cin, raw);
        if (raw.empty()) {
            send_error("No request received.");
            return 0;
        }

        std::string command = json_get(raw, "command");
        if (command == "ping") {
            WmcaClient client;
            send_ok("{\"status\":\"dll_loaded\"}");
            return 0;
        }
        if (command == "login") {
            HWND hwnd = create_message_window();
            if (!hwnd) {
                throw std::runtime_error("Failed to create message window.");
            }
            WmcaClient client;
            client.connect(hwnd);
            send_ok("{\"status\":\"login_ok\"}");
            return 0;
        }
        if (command == "order") {
            std::string symbol = json_get(raw, "symbol");
            std::string side = json_get(raw, "side");
            std::string price = json_get(raw, "price");
            std::string quantity = json_get(raw, "quantity");
            if (symbol.empty() || side.empty() || price.empty() || quantity.empty()) {
                send_error("symbol, side, price, and quantity are required.");
                return 0;
            }

            std::string tr_code = order_tr_code(side);
            std::string missing = required_env_state();
            bool live_enabled = env_yes("APIF_ENABLE_LIVE_TRADING");

            std::ostringstream data;
            data << "{\"accepted\":false,"
                 << "\"order_id\":\"\","
                 << "\"tr_code\":\"" << tr_code << "\","
                 << "\"tr_name\":\"" << order_tr_name(side) << "\","
                 << "\"symbol\":\"" << json_escape(symbol) << "\","
                 << "\"side\":\"" << json_escape(side) << "\","
                 << "\"price\":" << std::atoi(price.c_str()) << ","
                 << "\"quantity\":" << std::atoi(quantity.c_str()) << ",";
            if (!missing.empty()) {
                data << "\"message\":\"Live order blocked. Missing: " << json_escape(missing) << "\"}";
            } else if (!live_enabled) {
                data << "\"message\":\"Live order blocked. APIF_ENABLE_LIVE_TRADING is not YES.\"}";
            } else {
                data << "\"message\":\"Live order blocked. Native order transmission is not enabled in this safety build.\"}";
            }
            send_ok(data.str());
            return 0;
        }
        if (command != "quote") {
            send_error("Unknown command: " + command);
            return 0;
        }

        std::string symbol = json_get(raw, "symbol");
        if (symbol.empty()) {
            send_error("symbol is required.");
            return 0;
        }

        HWND hwnd = create_message_window();
        if (!hwnd) {
            throw std::runtime_error("Failed to create message window.");
        }

        WmcaClient client;
        client.connect(hwnd);
        int price = client.quote(hwnd, symbol);

        std::ostringstream data;
        data << "{\"symbol\":\"" << json_escape(symbol) << "\",\"price\":" << price << "}";
        send_ok(data.str());
        return 0;
    } catch (const std::exception& exc) {
        send_error(exc.what());
        return 0;
    }
}
