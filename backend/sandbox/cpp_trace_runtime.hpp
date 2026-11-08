// CodeLens native C++ trace runtime — included before instrumented user code.
//
// The instrumenter inserts `codelens_rt::step(LINE, "a", a, "b", b, ...)` before
// statements and a `codelens_rt::Frame` at the start of each function. Each step
// snapshots the in-scope variables into the same tagged JSON value model the
// Python tracer uses, so the backend reuses one visualisation pipeline.
// The trace is written to stderr between markers when the program ends, hits
// the step budget, or crashes (segfault / abort / divide by zero).
#include <bits/stdc++.h>

namespace codelens_rt {

struct Ctx {
    std::vector<std::string> steps;
    std::vector<const char*> frames;
    std::vector<std::string> rets;  // pending return value per frame (set by ret())
    std::vector<int> lines;  // last executed line per frame
    std::unordered_map<const void*, int> ids;
    int max_steps = 400;
    bool truncated = false;
    bool flushed = false;
};
// Heap-allocated and never destroyed: the atexit flush runs after static destructors.
inline Ctx& ctx() { static Ctx* c = new Ctx; return *c; }

// ---- stdout byte counter (so each step knows how much output existed) ----
struct CountBuf : std::streambuf {
    std::streambuf* dest = nullptr;
    size_t n = 0;
    int overflow(int c) override {
        if (c == EOF) return 0;
        ++n;
        return dest->sputc(static_cast<char>(c));
    }
    std::streamsize xsputn(const char* s, std::streamsize k) override { n += k; return dest->sputn(s, k); }
    int sync() override { return dest->pubsync(); }
};
inline CountBuf& outbuf() { static CountBuf* b = new CountBuf; return *b; }

// ---- JSON helpers ----
inline std::string esc(const std::string& s) {
    std::string o = "\"";
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += static_cast<char>(c); }
        else if (c == '\n') o += "\\n";
        else if (c < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); o += b; }
        else o += static_cast<char>(c);
    }
    return o + "\"";
}
inline int pid(const void* p) {
    auto& m = ctx().ids;
    auto it = m.find(p);
    if (it != m.end()) return it->second;
    int id = static_cast<int>(m.size()) + 1;
    m[p] = id;
    return id;
}

struct Seen { std::unordered_set<const void*> s; int budget = 300; };
constexpr size_t kMaxItems = 200;

template <class, class = void> struct has_next : std::false_type {};
template <class T> struct has_next<T, std::void_t<decltype(std::declval<T&>().next)>> : std::true_type {};
template <class, class = void> struct has_lr : std::false_type {};
template <class T> struct has_lr<T, std::void_t<decltype(std::declval<T&>().left), decltype(std::declval<T&>().right)>>
    : std::true_type {};
template <class, class = void> struct has_val : std::false_type {};
template <class T> struct has_val<T, std::void_t<decltype(std::declval<T&>().val)>> : std::true_type {};

// ---- value model (forward declarations so containers can nest) ----
inline std::string v(bool x, Seen&) { return x ? "true" : "false"; }
inline std::string v(char x, Seen&) { return esc(std::string(1, x)); }
inline std::string v(int x, Seen&) { return std::to_string(x); }
inline std::string v(long x, Seen&) { return std::to_string(x); }
inline std::string v(long long x, Seen&) { return std::to_string(x); }
inline std::string v(unsigned x, Seen&) { return std::to_string(x); }
inline std::string v(unsigned long x, Seen&) { return std::to_string(x); }
inline std::string v(unsigned long long x, Seen&) { return std::to_string(x); }
inline std::string v(short x, Seen&) { return std::to_string(x); }
inline std::string v(double x, Seen&) {
    if (!std::isfinite(x)) return R"({"t":"repr","v":")" + std::string(std::isnan(x) ? "nan" : x > 0 ? "inf" : "-inf") + "\"}";
    std::ostringstream o; o << std::setprecision(10) << x; return o.str();
}
inline std::string v(float x, Seen& s) { return v(static_cast<double>(x), s); }
inline std::string v(const std::string& x, Seen&) { return esc(x.size() > 200 ? x.substr(0, 200) + "…" : x); }
inline std::string v(const char* x, Seen&) { return x ? esc(x) : "null"; }

template <class T> std::string v(const T&, Seen&);  // fallback
template <class T> std::string v(T* const& p, Seen& s);
template <class T, class A> std::string v(const std::vector<T, A>& x, Seen& s);
template <class A> std::string v(const std::vector<bool, A>& x, Seen& s);
template <class T, class A> std::string v(const std::deque<T, A>& x, Seen& s);
template <class T, class A> std::string v(const std::list<T, A>& x, Seen& s);
template <class T, size_t N> std::string v(const std::array<T, N>& x, Seen& s);
template <class K, class C, class A> std::string v(const std::set<K, C, A>& x, Seen& s);
template <class K, class C, class A> std::string v(const std::multiset<K, C, A>& x, Seen& s);
template <class K, class H, class E, class A> std::string v(const std::unordered_set<K, H, E, A>& x, Seen& s);
template <class K, class V, class C, class A> std::string v(const std::map<K, V, C, A>& x, Seen& s);
template <class K, class V, class H, class E, class A> std::string v(const std::unordered_map<K, V, H, E, A>& x, Seen& s);
template <class A, class B> std::string v(const std::pair<A, B>& x, Seen& s);
template <class T, class C> std::string v(const std::stack<T, C>& x, Seen& s);
template <class T, class C> std::string v(const std::queue<T, C>& x, Seen& s);
template <class T, class C, class P> std::string v(const std::priority_queue<T, C, P>& x, Seen& s);

template <class It> std::string seq(const char* tag, It b, It e, Seen& s) {
    std::string o = std::string(R"({"t":")") + tag + R"(","v":[)";
    size_t n = 0;
    for (; b != e && n < kMaxItems; ++b, ++n) { if (n) o += ","; o += v(*b, s); }
    return o + "]}";
}
template <class It> std::string dict(It b, It e, Seen& s) {
    std::string o = R"({"t":"dict","v":[)";
    size_t n = 0;
    for (; b != e && n < kMaxItems; ++b, ++n) { if (n) o += ","; o += "[" + v(b->first, s) + "," + v(b->second, s) + "]"; }
    return o + "]}";
}

template <class T> std::string v(const T&, Seen&) { return R"({"t":"repr","v":"…"})"; }
template <class T, class A> std::string v(const std::vector<T, A>& x, Seen& s) { return seq("list", x.begin(), x.end(), s); }
template <class A> std::string v(const std::vector<bool, A>& x, Seen&) {
    std::string o = R"({"t":"list","v":[)";
    for (size_t i = 0; i < x.size() && i < kMaxItems; ++i) { if (i) o += ","; o += x[i] ? "true" : "false"; }
    return o + "]}";
}
template <class T, class A> std::string v(const std::deque<T, A>& x, Seen& s) { return seq("deque", x.begin(), x.end(), s); }
template <class T, class A> std::string v(const std::list<T, A>& x, Seen& s) { return seq("list", x.begin(), x.end(), s); }
template <class T, size_t N> std::string v(const std::array<T, N>& x, Seen& s) { return seq("list", x.begin(), x.end(), s); }
template <class K, class C, class A> std::string v(const std::set<K, C, A>& x, Seen& s) { return seq("set", x.begin(), x.end(), s); }
template <class K, class C, class A> std::string v(const std::multiset<K, C, A>& x, Seen& s) { return seq("list", x.begin(), x.end(), s); }
template <class K, class H, class E, class A> std::string v(const std::unordered_set<K, H, E, A>& x, Seen& s) {
    std::vector<K> items(x.begin(), x.end());
    std::sort(items.begin(), items.end());
    return seq("set", items.begin(), items.end(), s);
}
template <class K, class V, class C, class A> std::string v(const std::map<K, V, C, A>& x, Seen& s) { return dict(x.begin(), x.end(), s); }
template <class K, class V, class H, class E, class A> std::string v(const std::unordered_map<K, V, H, E, A>& x, Seen& s) {
    return dict(x.begin(), x.end(), s);
}
template <class A, class B> std::string v(const std::pair<A, B>& x, Seen& s) {
    return R"({"t":"tuple","v":[)" + v(x.first, s) + "," + v(x.second, s) + "]}";
}
template <class T, class C> std::string v(const std::stack<T, C>& x, Seen& s) {
    std::stack<T, C> c = x; std::vector<T> items;
    while (!c.empty() && items.size() < kMaxItems) { items.push_back(c.top()); c.pop(); }
    std::reverse(items.begin(), items.end());  // bottom → top
    return seq("list", items.begin(), items.end(), s);
}
template <class T, class C> std::string v(const std::queue<T, C>& x, Seen& s) {
    std::queue<T, C> c = x; std::vector<T> items;
    while (!c.empty() && items.size() < kMaxItems) { items.push_back(c.front()); c.pop(); }
    return seq("deque", items.begin(), items.end(), s);
}
template <class T, class C, class P> std::string v(const std::priority_queue<T, C, P>& x, Seen& s) {
    std::priority_queue<T, C, P> c = x; std::vector<T> items;
    while (!c.empty() && items.size() < kMaxItems) { items.push_back(c.top()); c.pop(); }
    return seq("list", items.begin(), items.end(), s);
}
// Node pointers (any struct with val + next, or val + left/right): object graph with cycle refs.
template <class T> std::string v(T* const& p, Seen& s) {
    if (p == nullptr) return "null";
    if constexpr (has_val<T>::value && (has_next<T>::value || has_lr<T>::value)) {
        int id = pid(p);
        if (s.s.count(p) || --s.budget < 0) return R"({"t":"ref","id":)" + std::to_string(id) + "}";
        s.s.insert(p);
        std::string f = R"("val":)" + v(p->val, s);
        if constexpr (has_next<T>::value) f += R"(,"next":)" + v(p->next, s);
        if constexpr (has_lr<T>::value) f += R"(,"left":)" + v(p->left, s) + R"(,"right":)" + v(p->right, s);
        const char* cls = has_next<T>::value ? "ListNode" : "TreeNode";
        return R"({"t":"obj","cls":")" + std::string(cls) + R"(","id":)" + std::to_string(id) + R"(,"f":{)" + f + "}}";
    } else {
        return R"({"t":"repr","v":"pointer"})";
    }
}

// ---- recording ----
inline void flush(const char* error) {
    auto& c = ctx();
    if (c.flushed) return;
    c.flushed = true;
    std::cout.flush();
    std::string doc = R"({"steps":[)";
    for (size_t i = 0; i < c.steps.size(); ++i) { if (i) doc += ","; doc += c.steps[i]; }
    doc += R"(],"truncated":)" + std::string(c.truncated ? "true" : "false");
    doc += R"(,"error":)" + (error ? esc(error) : std::string("null")) + "}";
    std::fputs("\n@@CODELENS_TRACE@@\n", stderr);
    std::fputs(doc.c_str(), stderr);
    std::fputs("\n@@CODELENS_TRACE_END@@\n", stderr);
    std::fflush(stderr);
}

inline void add(std::string&, Seen&) {}
template <class T, class... R> void add(std::string& o, Seen& s, const char* name, const T& x, const R&... rest) {
    if (o.size() > 1) o += ",";
    s.budget = 300;
    o += esc(name) + ":" + v(x, s);
    add(o, s, rest...);
}

inline void guard_budget() {
    auto& c = ctx();
    if (static_cast<int>(c.steps.size()) >= c.max_steps) {
        c.truncated = true;
        flush(nullptr);
        std::_Exit(0);
    }
}

inline std::string event(const char* kind, int line, const std::string& locals, const std::string* ret) {
    auto& c = ctx();
    const char* fn = c.frames.empty() ? "main" : c.frames.back();
    int depth = c.frames.empty() ? 0 : static_cast<int>(c.frames.size()) - 1;
    std::string e = R"({"line":)" + (line > 0 ? std::to_string(line) : std::string("null")) + R"(,"event":")" + kind +
                    R"(","func":)" + esc(fn) + R"(,"depth":)" + std::to_string(depth) + R"(,"out":)" +
                    std::to_string(outbuf().n) + R"(,"locals":)" + locals + R"(,"globals":{})";
    if (ret) e += R"(,"ret":)" + (ret->empty() ? std::string("null") : *ret);
    return e + "}";
}

// Function frame: records the call (with arguments) and the return (with value).
struct Frame {
    template <class... A> Frame(int line, const char* name, const A&... args) {
        auto& c = ctx();
        c.frames.push_back(name);
        c.rets.emplace_back();
        c.lines.push_back(line);
        guard_budget();
        std::string locals = "{";
        Seen seen;
        add(locals, seen, args...);
        c.steps.push_back(event("call", line, locals + "}", nullptr));
    }
    ~Frame() {
        auto& c = ctx();
        if (c.frames.empty()) return;
        if (static_cast<int>(c.steps.size()) < c.max_steps) {
            c.steps.push_back(event("return", c.lines.back(), "{}", &c.rets.back()));
        }
        c.frames.pop_back();
        c.rets.pop_back();
        c.lines.pop_back();
    }
};

// Wraps `return expr;` → `return codelens_rt::ret(expr);` to capture the value.
template <class T> T&& ret(T&& value) {
    auto& c = ctx();
    if (!c.rets.empty()) { Seen s; c.rets.back() = v(value, s); }
    return std::forward<T>(value);
}

template <class... A> void step(int line, const A&... vars) {
    auto& c = ctx();
    guard_budget();
    std::string locals = "{";
    Seen seen;
    add(locals, seen, vars...);
    if (!c.lines.empty()) c.lines.back() = line;
    c.steps.push_back(event("line", line, locals + "}", nullptr));
}

inline void on_signal(int sig) {
    flush(sig == SIGSEGV ? "Segmentation fault (null pointer or out-of-bounds access?)"
          : sig == SIGFPE ? "Floating point exception (division by zero?)"
                          : "Aborted");
    std::_Exit(128 + sig);
}

struct Installer {
    Installer() {
        outbuf().dest = std::cout.rdbuf();
        std::cout.rdbuf(&outbuf());
        std::signal(SIGSEGV, on_signal);
        std::signal(SIGFPE, on_signal);
        std::signal(SIGABRT, on_signal);
        std::atexit([] { flush(nullptr); });
    }
};
inline Installer installer;

}  // namespace codelens_rt
