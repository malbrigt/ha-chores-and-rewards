"""Sidebar panel registration and static frontend file."""

from homeassistant.components import frontend

from custom_components.chores_and_rewards.const import PANEL_URL, STATIC_URL


async def test_panel_registered_and_removed(hass, setup_entry):
    entry = await setup_entry()
    panels = hass.data[frontend.DATA_PANELS]
    panel = panels[PANEL_URL]
    assert panel.require_admin
    assert panel.sidebar_title == "Gjøremål"
    module_url = panel.config["_panel_custom"]["module_url"]
    assert module_url.startswith(f"{STATIC_URL}/panel.js?v=")
    assert panel.config["_panel_custom"]["name"] == "chores-and-rewards-panel"

    await hass.config_entries.async_reload(entry.entry_id)  # no "overwriting panel" error
    await hass.async_block_till_done()
    assert PANEL_URL in hass.data[frontend.DATA_PANELS]

    await hass.config_entries.async_unload(entry.entry_id)
    assert PANEL_URL not in hass.data[frontend.DATA_PANELS]


async def test_static_js_served(hass, setup_entry, hass_client):
    await setup_entry()
    client = await hass_client()
    resp = await client.get(f"{STATIC_URL}/panel.js")
    assert resp.status == 200
    body = await resp.text()
    assert 'customElements.define("chores-and-rewards-panel"' in body
