"""Human-like interaction utilities for anti-detection."""

import random
import time


def human_type(page, selector: str, text: str):
    """Type text with random delays between keystrokes to simulate human typing."""
    page.click(selector)
    time.sleep(random.uniform(0.2, 0.5))

    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.04, 0.18))


def human_delay(min_s: float = 0.5, max_s: float = 2.0):
    """Random delay simulating human thinking or reading."""
    time.sleep(random.uniform(min_s, max_s))


def human_click(page, selector: str):
    """Click an element with slight random offset to appear natural."""
    element = page.locator(selector)
    element.wait_for(state="visible", timeout=10_000)

    box = element.bounding_box()
    if box:
        x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
        page.mouse.move(x, y, steps=random.randint(5, 15))
        human_delay(0.1, 0.3)
        page.mouse.click(x, y)
    else:
        element.click()


def human_scroll(page, direction: str = "down", amount: int = 300):
    """Scroll the page with random variation."""
    delta = random.randint(amount - 50, amount + 50)
    if direction == "up":
        delta = -delta
    page.mouse.wheel(0, delta)
    human_delay(0.3, 0.8)


def random_mouse_movement(page):
    """Move mouse to random positions to simulate idle human behavior."""
    for _ in range(random.randint(2, 5)):
        x = random.randint(200, 1600)
        y = random.randint(200, 800)
        page.mouse.move(x, y, steps=random.randint(10, 25))
        human_delay(0.1, 0.4)
