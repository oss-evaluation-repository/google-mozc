// Copyright 2010, Google Inc.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
//
//     * Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above
// copyright notice, this list of conditions and the following disclaimer
// in the documentation and/or other materials provided with the
// distribution.
//     * Neither the name of Google Inc. nor the names of its
// contributors may be used to endorse or promote products derived from
// this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#include <set>

#include "base/scoped_ptr.h"
#include "testing/base/public/gunit.h"
#include "session/commands.pb.h"
#include "unix/ibus/key_translator.h"

namespace mozc {
namespace ibus {

const guint special_keys[] = {
  IBUS_space,
  IBUS_Return,
  IBUS_Left,
  IBUS_Right,
  IBUS_Up,
  IBUS_Down,
  IBUS_Escape,
  IBUS_Delete,
  IBUS_BackSpace,
  IBUS_Insert,
  IBUS_Henkan,
  IBUS_Muhenkan,
  IBUS_Hiragana,
  IBUS_Katakana,
  IBUS_Eisu_toggle,
  IBUS_Home,
  IBUS_End,
  IBUS_Tab,
  IBUS_F1,
  IBUS_F2,
  IBUS_F3,
  IBUS_F4,
  IBUS_F5,
  IBUS_F6,
  IBUS_F7,
  IBUS_F8,
  IBUS_F9,
  IBUS_F10,
  IBUS_F11,
  IBUS_F12,
  IBUS_F13,
  IBUS_F14,
  IBUS_F15,
  IBUS_F16,
  IBUS_F17,
  IBUS_F18,
  IBUS_F19,
  IBUS_F20,
  IBUS_F21,
  IBUS_F22,
  IBUS_F23,
  IBUS_F24,
  IBUS_Page_Up,
  IBUS_Page_Down,
  IBUS_KP_0,
  IBUS_KP_1,
  IBUS_KP_2,
  IBUS_KP_3,
  IBUS_KP_4,
  IBUS_KP_5,
  IBUS_KP_6,
  IBUS_KP_7,
  IBUS_KP_8,
  IBUS_KP_9,
  IBUS_KP_Equal,
  IBUS_KP_Multiply,
  IBUS_KP_Add,
  IBUS_KP_Separator,
  IBUS_KP_Subtract,
  IBUS_KP_Decimal,
  IBUS_KP_Divide,
  IBUS_KP_Space,
  IBUS_KP_Tab,
  IBUS_KP_Enter,
  IBUS_KP_Home,
  IBUS_KP_Left,
  IBUS_KP_Up,
  IBUS_KP_Right,
  IBUS_KP_Down,
  IBUS_KP_Page_Up,
  IBUS_KP_Page_Down,
  IBUS_KP_End,
  IBUS_KP_Delete,
  IBUS_KP_Insert,
  IBUS_ISO_Left_Tab,
};

const commands::KeyEvent::SpecialKey mapped_special_keys[] = {
  commands::KeyEvent::SPACE,
  commands::KeyEvent::ENTER,
  commands::KeyEvent::LEFT,
  commands::KeyEvent::RIGHT,
  commands::KeyEvent::UP,
  commands::KeyEvent::DOWN,
  commands::KeyEvent::ESCAPE,
  commands::KeyEvent::DEL,
  commands::KeyEvent::BACKSPACE,
  commands::KeyEvent::INSERT,
  commands::KeyEvent::HENKAN,
  commands::KeyEvent::MUHENKAN,
  commands::KeyEvent::KANA,
  commands::KeyEvent::KANA,
  commands::KeyEvent::EISU,
  commands::KeyEvent::HOME,
  commands::KeyEvent::END,
  commands::KeyEvent::TAB,
  commands::KeyEvent::F1,
  commands::KeyEvent::F2,
  commands::KeyEvent::F3,
  commands::KeyEvent::F4,
  commands::KeyEvent::F5,
  commands::KeyEvent::F6,
  commands::KeyEvent::F7,
  commands::KeyEvent::F8,
  commands::KeyEvent::F9,
  commands::KeyEvent::F10,
  commands::KeyEvent::F11,
  commands::KeyEvent::F12,
  commands::KeyEvent::F13,
  commands::KeyEvent::F14,
  commands::KeyEvent::F15,
  commands::KeyEvent::F16,
  commands::KeyEvent::F17,
  commands::KeyEvent::F18,
  commands::KeyEvent::F19,
  commands::KeyEvent::F20,
  commands::KeyEvent::F21,
  commands::KeyEvent::F22,
  commands::KeyEvent::F23,
  commands::KeyEvent::F24,
  commands::KeyEvent::PAGE_UP,
  commands::KeyEvent::PAGE_DOWN,
  commands::KeyEvent::NUMPAD0,
  commands::KeyEvent::NUMPAD1,
  commands::KeyEvent::NUMPAD2,
  commands::KeyEvent::NUMPAD3,
  commands::KeyEvent::NUMPAD4,
  commands::KeyEvent::NUMPAD5,
  commands::KeyEvent::NUMPAD6,
  commands::KeyEvent::NUMPAD7,
  commands::KeyEvent::NUMPAD8,
  commands::KeyEvent::NUMPAD9,
  commands::KeyEvent::EQUALS,
  commands::KeyEvent::MULTIPLY,
  commands::KeyEvent::ADD,
  commands::KeyEvent::SEPARATOR,
  commands::KeyEvent::SUBTRACT,
  commands::KeyEvent::DECIMAL,
  commands::KeyEvent::DIVIDE,
  commands::KeyEvent::SPACE,
  commands::KeyEvent::TAB,
  commands::KeyEvent::ENTER,
  commands::KeyEvent::HOME,
  commands::KeyEvent::LEFT,
  commands::KeyEvent::UP,
  commands::KeyEvent::RIGHT,
  commands::KeyEvent::DOWN,
  commands::KeyEvent::PAGE_UP,
  commands::KeyEvent::PAGE_DOWN,
  commands::KeyEvent::END,
  commands::KeyEvent::DEL,
  commands::KeyEvent::INSERT,
  commands::KeyEvent::TAB,
};

const guint modifier_masks[] = {
  IBUS_SHIFT_MASK,
  IBUS_CONTROL_MASK,
  IBUS_MOD1_MASK,
};

const commands::KeyEvent::ModifierKey mapped_modifiers[] = {
  commands::KeyEvent::SHIFT,
  commands::KeyEvent::CTRL,
  commands::KeyEvent::ALT,
};

class KeyTranslatorTest : public testing::Test {
 protected:
  KeyTranslatorTest() {}
  ~KeyTranslatorTest() {}

  virtual void SetUp() {
    translator_.reset(new KeyTranslator);
  }

  scoped_ptr<KeyTranslator> translator_;
};

TEST_F(KeyTranslatorTest, TranslateAscii) {
  commands::KeyEvent out;
  // ' ' (0x20) is treated as a special key by Mozc.
  EXPECT_TRUE(translator_->Translate(0x20, 0, 0, config::Config::ROMAN, true,
                                     &out));
  EXPECT_FALSE(out.has_key_code());
  EXPECT_TRUE(out.has_special_key());
  EXPECT_EQ(0, out.modifier_keys_size());

  for (char c = 0x21; c < 0x7f; ++c) {
    EXPECT_TRUE(translator_->Translate(c, 0, 0, config::Config::ROMAN, true,
                                       &out));
    EXPECT_TRUE(out.has_key_code());
    EXPECT_FALSE(out.has_special_key());
    EXPECT_EQ(c, out.key_code());
    EXPECT_EQ(0, out.modifier_keys_size());
  }
}

TEST_F(KeyTranslatorTest, TranslateSpecial) {
  commands::KeyEvent out;
  for (int i = 0; i < arraysize(special_keys); ++i) {
    EXPECT_TRUE(translator_->Translate(special_keys[i], 0, 0,
                                       config::Config::ROMAN, true, &out));
    EXPECT_FALSE(out.has_key_code());
    EXPECT_TRUE(out.has_special_key());
    EXPECT_EQ(mapped_special_keys[i], out.special_key());
    EXPECT_EQ(0, out.modifier_keys_size());
  }
}

TEST_F(KeyTranslatorTest, TranslateModifierMasks) {
  const int mask_combination_size = (1 << arraysize(modifier_masks));
  commands::KeyEvent out;
  for (int i = 0; i < mask_combination_size; ++i) {
    guint modifier = 0;
    set<commands::KeyEvent::ModifierKey> mapped_modifier;
    for (int j = 0; j < arraysize(modifier_masks); ++j) {
      if ((1 << j) & i) {
        modifier |= modifier_masks[j];
        mapped_modifier.insert(mapped_modifiers[j]);
      }
    }

    EXPECT_TRUE(translator_->Translate(IBUS_F1, 0, modifier,
                                       config::Config::ROMAN, true, &out));
    EXPECT_EQ(mapped_modifier.size(), out.modifier_keys_size());

    set<commands::KeyEvent::ModifierKey> actual_modifier;
    for (int j = 0; j < out.modifier_keys_size(); ++j) {
      actual_modifier.insert(out.modifier_keys(j));
    }
    EXPECT_TRUE(mapped_modifier == actual_modifier);

    // Shift modifier key is dropped for ascii characters.
    EXPECT_TRUE(translator_->Translate(IBUS_A, 0, modifier,
                                       config::Config::ROMAN, true, &out));
    if (mapped_modifier.find(commands::KeyEvent::SHIFT) !=
        mapped_modifier.end()) {
      mapped_modifier.erase(commands::KeyEvent::SHIFT);
    }
    EXPECT_EQ(mapped_modifier.size(), out.modifier_keys_size());
    set<commands::KeyEvent::ModifierKey> actual_modifier2;
    for (int j = 0; j < out.modifier_keys_size(); ++j) {
      actual_modifier2.insert(out.modifier_keys(j));
    }
    EXPECT_TRUE(mapped_modifier == actual_modifier2);
  }
}

TEST_F(KeyTranslatorTest, TranslateUnknow) {
  commands::KeyEvent out;
  EXPECT_FALSE(translator_->Translate(IBUS_VoidSymbol, 0, 0,
                                      config::Config::ROMAN, true, &out));

  // Mozc does not support F25 - F35.
  EXPECT_FALSE(translator_->Translate(IBUS_F25, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F26, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F27, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F28, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F29, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F30, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F31, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F32, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F33, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F34, 0, 0, config::Config::ROMAN,
                                      true, &out));
  EXPECT_FALSE(translator_->Translate(IBUS_F35, 0, 0, config::Config::ROMAN,
                                      true, &out));
}

}  // namespace ibus
}  // namespace mozc
