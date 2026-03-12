"""
story_system.py — Fragmentia
AI Motoru: Google Gemini → Groq (llama-3.3-70b) + Threading
Değişiklikler:
  - google.generativeai tamamen kaldırıldı
  - Groq API (urllib tabanlı, sıfır bağımlılık) eklendi
  - send_ai_message() → threading ile async hale getirildi (main thread donmuyor)
  - generate_npc_response() → GroqNPCManager'a devredildi
  - Model fallback zinciri: 5 model sırayla deneniyor
  - Arapça/yanlış dil filtresi eklendi (Türkçe zorunlu)
  - StoryManager arayüzü (main.py uyumluluğu) korundu
"""

import pygame
import json
import re
import math
import random
import threading
import urllib.request
import urllib.error
import ssl
import unicodedata
import warnings

from settings import (
    GROQ_API_KEY, GROQ_URL, GROQ_MODELS,
    FRAGMENTIA_SYSTEM_PROMPT,
    STORY_CHAPTERS,
)

# SSL sertifikası doğrulamasını atla (corporate proxy / self-signed uyumluluğu)
_SSL_CTX = ssl._create_unverified_context()

# ============================================================
# GROQ API YARDIMCI
# ============================================================

def _groq_call(messages: list, api_key: str, max_tokens: int = 200) -> str:
    """
    Groq API'ye istek atar. Model fallback zinciri ile 5 modeli sırayla dener.
    Tüm denemeler başarısız olursa hata mesajı döner.
    Thread-safe: GIL altında güvenle çağrılabilir.
    """
    if not api_key:
        return "[HATA] API anahtarı tanımlanmamış. settings.py → GROQ_API_KEY"

    for model_name in GROQ_MODELS:
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.9,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GROQ_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                body = json.loads(resp.read())
                reply = body["choices"][0]["message"]["content"].strip()

                # ── Dil filtresi: Arapça / başka alfabe gelirse aynı modeli tekrar dene ──
                arabic_count = sum(
                    1 for c in reply
                    if unicodedata.name(c, "").startswith("ARABIC")
                )
                if arabic_count > 2:
                    # System prompt'a Türkçe zorunluluğunu tekrar vurgula
                    messages[-1]["content"] += (
                        "\n\nÖNEMLİ: SADECE Türkçe yaz. Başka alfabe kesinlikle yasak."
                    )
                    continue  # aynı modeli yeniden dene

                return reply

        except urllib.error.HTTPError as e:
            code = e.code
            if code in (429, 503, 502):
                continue          # rate-limit veya geçici hata → sıradaki model
            try:
                err_body = json.loads(e.read().decode())
                msg = err_body.get("error", {}).get("message", str(e))[:120]
            except Exception:
                msg = str(e)[:120]
            return f"[API HATASI {code}] {msg}"

        except Exception as ex:
            continue             # ağ hatası → sıradaki model

    return "[BAĞLANTI KESİLDİ] Tüm modeller yanıt vermedi. Tekrar dene."


# ============================================================
# GROQ NPC MANAGER — NPC'lere özgü async chat yöneticisi
# ============================================================

class GroqNPCManager:
    """
    Entities.py → NPC sınıfı tarafından kullanılır.
    Her NPC kendi history'sini tutar; bu sınıf sadece API çağrısını
    worker thread'de yapar ve sonucu npc.ai_response'a yazar.
    """

    def __init__(self):
        self.api_key = GROQ_API_KEY

    def send_async(self, npc, player_msg: str, karma: int = 0):
        """
        Oyuncunun mesajını NPC'ye gönderir.
        Ana thread'i bloklamaz — threading.Thread kullanır.

        npc: entities.NPC instance (history, loading, ai_response, name, system_prompt alanları beklenir)
        """
        npc.history.append({"role": "user", "text": player_msg})
        npc.loading = True
        npc.ai_response = ""
        npc.error = ""

        def worker():
            # Sohbet geçmişini Groq mesaj formatına çevir
            messages = [{"role": "system", "content": self._build_system(npc, karma)}]
            for m in npc.history:
                role = "user" if m["role"] == "user" else "assistant"
                messages.append({"role": role, "content": m["text"]})

            reply = _groq_call(messages, self.api_key, max_tokens=200)

            npc.history.append({"role": "model", "text": reply})
            npc.ai_response = reply
            npc.loading = False
            npc._scroll_to_bottom = True

        threading.Thread(target=worker, daemon=True).start()

    def _build_system(self, npc, karma: int) -> str:
        """
        NPC'nin system prompt'una karma durumuna göre ek bağlam ekler.
        """
        base = npc.system_prompt or npc.prompt or (
            f"Sen Fragmentia adlı distopik oyunun bir NPC'sisin. Adin {npc.name}. "
            "Kısa, karakterine uygun Türkçe cevaplar ver."
        )

        karma_note = ""
        if karma >= 50:
            karma_note = (
                "\nOYUNCU BAĞLAMI: Bu kişi yardımsever ve iyi kalpli biri. "
                "Ona biraz daha sıcak ve açık davranabilirsin."
            )
        elif karma <= -50:
            karma_note = (
                "\nOYUNCU BAĞLAMI: Bu kişi çok şiddet uygulamış biri. "
                "Sana güvenmiyorsun, temkinli ve soğuk konuş."
            )

        return base + karma_note


# ============================================================
# STORY MANAGER — Ana hikaye/diyalog yöneticisi (main.py arayüzü korundu)
# ============================================================

class StoryManager:
    def __init__(self):
        self.current_text  = ""
        self.display_text  = ""
        self.char_index    = 0.0
        self.state         = "IDLE"   # TYPING | WAITING_INPUT | THINKING | FINISHED
        self.speaker       = ""
        self.text_speed    = 0.5
        self.waiting_for_click = False
        self.is_cutscene   = False

        # ── AI durumu ─────────────────────────────────────
        self.ai_active          = False
        self.ai_thinking        = False
        self._pending_response  = None   # thread'den gelen yanıt burada birikir
        self._response_lock     = threading.Lock()
        self.conversation_history = []

        # ── Bölüm sistemi ─────────────────────────────────
        self.current_chapter = 1
        self.dialogue_index  = 0
        self.chapter_data    = None
        self.dialogue_queue  = []

        # ── Fizik manipülasyonu (Vasi komutları) ──────────
        self.world_modifiers = {
            "gravity_mult": 1.0,
            "speed_mult":   1.0,
            "glitch_mode":  False,
        }

        self._setup_ai()

    # ----------------------------------------------------------
    # KURULUM
    # ----------------------------------------------------------

    def _setup_ai(self):
        """Groq bağlantısını doğrular."""
        if not GROQ_API_KEY:
            print("UYARI: GROQ_API_KEY boş. settings.py → GROQ_API_KEY")
            self.ai_active = False
            return
        self.ai_active = True
        print("FRAGMENTIA VASI PROTOKOLÜ: AKTİF (Groq / llama-3.3-70b)")

    # ----------------------------------------------------------
    # BÖLÜM & DİYALOG
    # ----------------------------------------------------------

    def load_chapter(self, chapter_id: int):
        self.current_chapter = chapter_id
        self.chapter_data    = STORY_CHAPTERS.get(chapter_id)
        self.dialogue_queue  = []

        if self.chapter_data:
            for line in self.chapter_data["dialogues"]:
                self.dialogue_queue.append(line)
            self.next_line()

    def next_line(self):
        if self.dialogue_queue:
            data = self.dialogue_queue.pop(0)
            self.speaker     = data["speaker"]
            self.current_text = data["text"]
            self.is_cutscene  = data.get("type", "chat") == "cutscene"
            self.display_text = ""
            self.char_index   = 0.0
            self.state        = "TYPING"
            self.waiting_for_click = False
        else:
            self.state = "FINISHED"

    def set_dialogue(self, speaker: str, text: str, is_cutscene: bool = False):
        self.speaker      = speaker
        self.current_text = text
        self.display_text = ""
        self.char_index   = 0
        self.state        = "TYPING"
        self.waiting_for_click = False
        self.is_cutscene  = is_cutscene

    # ----------------------------------------------------------
    # ANA HİKAYE AI (Vasi) — async
    # ----------------------------------------------------------

    def send_ai_message(self, user_text: str, game_context: dict = None):
        """
        Vasi (ana hikaye AI) ile konuşur.
        İstek threading.Thread ile gönderilir — main loop donmaz.
        """
        if not self.ai_active:
            self.set_dialogue("SİSTEM", "BAĞLANTI HATASI: Vasi'ye ulaşılamıyor.")
            return

        context_str = ""
        if game_context:
            context_str = (
                f"[SİSTEM VERİSİ: Skor={int(game_context.get('score', 0))}, "
                f"Ölüm={game_context.get('deaths', 0)}]. "
            )

        self.ai_thinking  = True
        self.speaker      = "VASI"
        self.current_text = "Analiz ediliyor..."
        self.display_text = "Analiz ediliyor..."
        self.state        = "THINKING"

        self.conversation_history.append(
            {"role": "user", "content": context_str + user_text}
        )

        def worker():
            messages = [{"role": "system", "content": FRAGMENTIA_SYSTEM_PROMPT}]
            messages.extend(self.conversation_history)

            raw_text = _groq_call(messages, GROQ_API_KEY, max_tokens=300)
            clean_text, commands = self._extract_commands(raw_text)

            if commands:
                self._apply_world_modifiers(commands)

            self.conversation_history.append(
                {"role": "assistant", "content": clean_text}
            )

            with self._response_lock:
                self._pending_response = ("VASI", clean_text)

        threading.Thread(target=worker, daemon=True).start()

    # ----------------------------------------------------------
    # NPC YANITI (legacy arayüz — entities.NPC.send_message içinden çağrılabilir)
    # ----------------------------------------------------------

    def generate_npc_response(self, npc, user_text: str, history: list) -> str:
        """
        Senkron NPC yanıtı üretir (eski arayüz, geriye dönük uyumluluk).
        Yeni kod için entities.NPC içindeki async send_message tercih edilmeli.
        """
        if not self.ai_active:
            return "AI Sistemi çevrimdışı."

        # Son 5 mesajı al
        history_text = "".join(
            f"{'Oyuncu' if m['role'] == 'user' else npc.name}: {m['text']}\n"
            for m in history[-5:]
        )

        system_prompt = (
            f"Rol Yapma: Sen {npc.name}'sın. Kişilik: {npc.personality_type}. "
            f"Görev/Rol: \"{npc.prompt}\". "
            "Evren: Fragmentia (siberpunk, distopik). "
            "Sadece Türkçe, maks 3 kısa cümle. "
            f"Geçmiş:\n{history_text}"
            f"{npc.name} olarak cevap ver:"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_text},
        ]
        return _groq_call(messages, GROQ_API_KEY, max_tokens=200)

    # ----------------------------------------------------------
    # GÜNCELLEME DÖNGÜSÜ
    # ----------------------------------------------------------

    def update(self, dt: float):
        # Bekleyen async yanıtı uygula
        with self._response_lock:
            if self._pending_response is not None:
                speaker, text = self._pending_response
                self._pending_response = None
                self.ai_thinking  = False
                self.speaker      = speaker
                self.current_text = text
                self.char_index   = 0
                self.state        = "TYPING"

        if self.state == "TYPING":
            self.char_index += self.text_speed * (dt * 60)
            if int(self.char_index) > len(self.current_text):
                self.char_index = len(self.current_text)
                self.state      = "WAITING_INPUT"
                self.waiting_for_click = True
            self.display_text = self.current_text[:int(self.char_index)]

        elif self.state == "THINKING":
            dots = "." * (int(pygame.time.get_ticks() / 500) % 4)
            self.display_text = f"VASI BAĞLANIYOR{dots}"

    def handle_input(self) -> bool:
        if self.state == "TYPING":
            self.char_index   = len(self.current_text)
            self.display_text = self.current_text
            self.state        = "WAITING_INPUT"
            self.waiting_for_click = True
            return False
        elif self.state == "WAITING_INPUT":
            if not self.ai_active:
                self.next_line()
            self.waiting_for_click = False
            return True
        return False

    # ----------------------------------------------------------
    # YARDIMCILAR
    # ----------------------------------------------------------

    def _extract_commands(self, text: str):
        """Metin içindeki JSON komutlarını ayırır (Vasi dünya manipülasyonu için)."""
        commands  = {}
        clean     = text

        # Markdown code block içi JSON
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                commands = json.loads(m.group(1))
                clean    = text.replace(m.group(0), "").strip()
                return clean, commands
            except Exception:
                pass

        # Düz JSON
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            try:
                commands = json.loads(m.group(1))
                clean    = text.replace(m.group(0), "").strip()
            except Exception:
                pass

        return clean, commands

    def _apply_world_modifiers(self, commands: dict):
        print(f"VASI DÜNYAYI DEĞİŞTİRİYOR: {commands}")
        if "gravity" in commands:
            self.world_modifiers["gravity_mult"] = float(commands["gravity"])
        if "speed" in commands:
            self.world_modifiers["speed_mult"]   = float(commands["speed"])
        if "glitch" in commands:
            self.world_modifiers["glitch_mode"]  = bool(commands["glitch"])


# ============================================================
# AI CHAT EFEKT (AIChatEffect) — main.py uyumluluğu korundu
# ============================================================

class AIChatEffect:
    """NEXUS AI görsel efektleri — değişmedi."""

    def __init__(self):
        self.timer = 0
        self.glitch_chars = "01FRAGMENTIA_ERROR_#!"

    def draw_ai_avatar(self, surface, x, y, size, thinking=False):
        center = (x, y)
        color  = (0, 255, 100) if not thinking else (255, 100, 0)
        t      = pygame.time.get_ticks()

        pygame.draw.circle(surface, (20, 20, 20), center, size)
        pygame.draw.circle(surface, color, center, size, 2)

        if thinking:
            ox = random.randint(-2, 2)
            oy = random.randint(-2, 2)
            pygame.draw.circle(surface, color, (x + ox, y + oy), size // 2)
        else:
            pulse = math.sin(t * 0.005) * 5
            pygame.draw.circle(surface, color, center, int(size // 2 + pulse))

        for i in range(3):
            angle = t * 0.002 + (i * 2.09)
            px = x + math.cos(angle) * (size + 10)
            py = y + math.sin(angle) * (size + 10)
            pygame.draw.line(surface, color, center, (int(px), int(py)), 1)


# ============================================================
# GLOBAL INSTANCE'LAR
# ============================================================

story_manager  = StoryManager()
ai_chat_effect = AIChatEffect()

# Groq NPC yöneticisi — entities.NPC tarafından import edilerek kullanılır
groq_npc_manager = GroqNPCManager()