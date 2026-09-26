package com.earnwage.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale

private val navy = Color(0xFF092733)
private val teal = Color(0xFF16A085)
private val gold = Color(0xFFF1D28C)
private val modules = listOf("inflation", "power", "currency", "compare", "salary", "jobs", "about")
private val languageNames = linkedMapOf("en" to "🇬🇧 English", "pt" to "🇵🇹 Português", "es" to "🇪🇸 Español", "de" to "🇩🇪 Deutsch", "fr" to "🇫🇷 Français", "it" to "🇮🇹 Italiano", "nl" to "🇳🇱 Nederlands")
private val words = mapOf(
    "en" to listOf("Inflation Explorer", "Purchasing Power", "Currency Explorer", "Country Comparison", "Salary Explorer", "Job Explorer", "About EarnWage", "Your salary. Your world.", "Get started", "Country", "Destination", "Occupation", "Search", "Annual gross salary", "User-entered accumulated inflation (%)", "Initial income", "Current income", "Start period", "End period", "Source / status", "Back", "Unavailable", "Loading", "Language"),
    "pt" to listOf("Explorar inflação", "Poder de compra", "Explorar moedas", "Comparar países", "Explorar salários", "Explorar empregos", "Sobre a EarnWage", "O teu salário. O teu mundo.", "Começar", "País", "Destino", "Profissão", "Pesquisar", "Salário bruto anual", "Inflação acumulada introduzida (%)", "Rendimento inicial", "Rendimento atual", "Período inicial", "Período final", "Fonte / estado", "Voltar", "Indisponível", "A carregar", "Idioma"),
    "es" to listOf("Explorar inflación", "Poder adquisitivo", "Explorar divisas", "Comparar países", "Explorar salarios", "Explorar empleos", "Acerca de EarnWage", "Tu salario. Tu mundo.", "Empezar", "País", "Destino", "Profesión", "Buscar", "Salario bruto anual", "Inflación acumulada introducida (%)", "Ingreso inicial", "Ingreso actual", "Periodo inicial", "Periodo final", "Fuente / estado", "Volver", "No disponible", "Cargando", "Idioma"),
    "de" to listOf("Inflation", "Kaufkraft", "Währungen", "Ländervergleich", "Gehälter", "Jobs", "Über EarnWage", "Dein Gehalt. Deine Welt.", "Starten", "Land", "Zielland", "Beruf", "Suchen", "Bruttojahresgehalt", "Eingegebene kumulierte Inflation (%)", "Anfangseinkommen", "Aktuelles Einkommen", "Anfangszeitraum", "Endzeitraum", "Quelle / Status", "Zurück", "Nicht verfügbar", "Lädt", "Sprache"),
    "fr" to listOf("Inflation", "Pouvoir d’achat", "Devises", "Comparer les pays", "Salaires", "Emplois", "À propos d’EarnWage", "Votre salaire. Votre monde.", "Commencer", "Pays", "Destination", "Profession", "Rechercher", "Salaire annuel brut", "Inflation cumulée saisie (%)", "Revenu initial", "Revenu actuel", "Période initiale", "Période finale", "Source / état", "Retour", "Indisponible", "Chargement", "Langue"),
    "it" to listOf("Inflazione", "Potere d’acquisto", "Valute", "Confronta paesi", "Stipendi", "Lavori", "Informazioni su EarnWage", "Il tuo stipendio. Il tuo mondo.", "Inizia", "Paese", "Destinazione", "Professione", "Cerca", "Stipendio lordo annuo", "Inflazione cumulata inserita (%)", "Reddito iniziale", "Reddito attuale", "Periodo iniziale", "Periodo finale", "Fonte / stato", "Indietro", "Non disponibile", "Caricamento", "Lingua"),
    "nl" to listOf("Inflatie", "Koopkracht", "Valuta", "Landen vergelijken", "Salarissen", "Banen", "Over EarnWage", "Jouw salaris. Jouw wereld.", "Beginnen", "Land", "Bestemming", "Beroep", "Zoeken", "Bruto jaarsalaris", "Ingevoerde cumulatieve inflatie (%)", "Begininkomen", "Huidig inkomen", "Beginperiode", "Eindperiode", "Bron / status", "Terug", "Niet beschikbaar", "Laden", "Taal")
)
private fun t(lang: String, index: Int) = words[lang]?.getOrNull(index) ?: words.getValue("en")[index]
private fun flag(code: String): String {
    if (code.length != 2 || code.any { it !in 'A'..'Z' }) return "🌐"
    val base = 0x1F1E6
    return String(Character.toChars(base + code[0].code - 65)) + String(Character.toChars(base + code[1].code - 65))
}
private fun query(value: String) = URLEncoder.encode(value, "UTF-8")
private suspend fun api(path: String): JSONObject = withContext(Dispatchers.IO) {
    val connection = URL(BuildConfig.API_BASE_URL + path).openConnection() as HttpURLConnection
    try {
        connection.connectTimeout = 12000
        connection.readTimeout = 18000
        connection.setRequestProperty("Accept", "application/json")
        val status = connection.responseCode
        val stream = if (status in 200..299) connection.inputStream else connection.errorStream
        val raw = stream?.bufferedReader()?.use { it.readText() } ?: ""
        if (status !in 200..299) throw IllegalStateException("HTTP $status: " + raw.take(180))
        JSONObject(raw)
    } finally { connection.disconnect() }
}
private data class Country(val code: String, val name: String, val currency: String)
private data class Job(val id: String, val label: String)
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { EarnWage() }
    }
}
@Composable private fun EarnWage() {
    var language by remember { mutableStateOf("en") }
    var screen by remember { mutableStateOf("cover") }
    var countries by remember { mutableStateOf(listOf<Country>()) }
    var occupations by remember { mutableStateOf(listOf<Job>()) }
    var country by remember { mutableStateOf("PT") }
    var destination by remember { mutableStateOf("US") }
    var occupation by remember { mutableStateOf("accountant") }
    var result by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var health by remember { mutableStateOf("Checking API…") }
    var annual by remember { mutableStateOf("") }
    var initial by remember { mutableStateOf("") }
    var current by remember { mutableStateOf("") }
    var inflation by remember { mutableStateOf("") }
    var start by remember { mutableStateOf("2020") }
    var end by remember { mutableStateOf("2026") }
    var currency by remember { mutableStateOf("USD") }
    var amount by remember { mutableStateOf("1000") }
    var request by remember { mutableStateOf("") }
    LaunchedEffect(Unit) {
        try {
            val h = api("/v1/health")
            health = "API: " + h.optString("status") + " · " + h.optString("version")
            val a = api("/v1/countries").optJSONArray("countries") ?: JSONArray()
            countries = (0 until a.length()).map { a.getJSONObject(it) }.map {
                Country(it.optString("code"), it.optString("name"), it.optString("currency"))
            }
        } catch (e: Exception) { health = "API unavailable: " + (e.message ?: "network error") }
    }
    LaunchedEffect(language) {
        try {
            val a = api("/v1/occupations?lang=" + query(language)).optJSONArray("occupations") ?: JSONArray()
            occupations = (0 until a.length()).map { a.getJSONObject(it) }.map { Job(it.optString("id"), it.optString("label")) }
        } catch (_: Exception) { occupations = emptyList() }
    }
    LaunchedEffect(request) {
        if (request.isNotBlank()) {
            loading = true
            result = ""
            try { result = api(request).toString(2) }
            catch (e: Exception) { result = "Unable to retrieve verified data: " + (e.message ?: "network error") }
            finally { loading = false }
        }
    }
    MaterialTheme(colorScheme = lightColorScheme(primary = teal, secondary = navy)) {
        Column(Modifier.fillMaxSize().background(Color(0xFFF5F8F8)).verticalScroll(rememberScrollState()).padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (screen == "cover") {
                Spacer(Modifier.height(45.dp))
                Image(painterResource(R.drawable.earnwage_hero), contentDescription = "EarnWage hero", modifier = Modifier.fillMaxWidth().height(245.dp), contentScale = ContentScale.Fit)
                Text("EarnWage", fontSize = 42.sp, fontWeight = FontWeight.Bold, color = navy)
                Text("Salary & Cost of Living", fontSize = 18.sp, color = teal)
                Text(t(language, 7), fontSize = 22.sp, color = navy)
                Text("Inflation · Purchasing power · Currencies · Salaries · Jobs")
                Button(onClick = { screen = "home" }) { Text(t(language, 8)) }
                LanguageSelector(language) { language = it }
                Text(health, fontSize = 12.sp)
            } else {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Image(painterResource(R.drawable.earnwage_logo), contentDescription = "EarnWage logo", modifier = Modifier.size(48.dp))
                    Text("EarnWage", fontSize = 26.sp, color = navy, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                    TextButton(onClick = { screen = "home"; result = ""; request = "" }) { Text(t(language, 20)) }
                }
                if (screen == "home") {
                    Text(t(language, 7), color = teal)
                    LanguageSelector(language) { language = it }
                    modules.forEachIndexed { index, key ->
                        Card(onClick = { screen = key; result = ""; request = "" }, modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = navy)) {
                            Text(t(language, index), color = Color.White, fontSize = 19.sp, modifier = Modifier.padding(18.dp))
                        }
                    }
                    Text(health, fontSize = 12.sp)
                } else {
                    val index = modules.indexOf(screen)
                    Text(t(language, index.coerceAtLeast(0)), fontSize = 23.sp, fontWeight = FontWeight.Bold, color = navy)
                    if (screen != "about") {
                        CountrySelector(t(language, 9), countries, country) { country = it }
                        if (screen == "compare") CountrySelector(t(language, 10), countries, destination) { destination = it }
                        if (screen in listOf("salary", "jobs", "compare")) JobSelector(t(language, 11), occupations, occupation) { occupation = it }
                    }
                    when (screen) {
                        "inflation" -> {
                            Text("Official national monthly HICP where supported. The current API does not yet provide a validated arbitrary start/end-period cumulative series.")
                            OutlinedTextField(start, { start = it }, label = { Text(t(language, 17)) }, modifier = Modifier.fillMaxWidth())
                            OutlinedTextField(end, { end = it }, label = { Text(t(language, 18)) }, modifier = Modifier.fillMaxWidth())
                            Text("Period fields are reserved for the forthcoming historical API. The current result is NOT a cumulative change between these dates.", color = teal)
                            Button(onClick = { request = "/v1/inflation/$country" }) { Text(t(language, 12)) }
                        }
                        "power" -> {
                            Text("Manual illustration only: enter the accumulated inflation for the chosen period. It is NOT fetched or verified by the API.")
                            OutlinedTextField(start, { start = it }, label = { Text(t(language, 17)) }, modifier = Modifier.fillMaxWidth())
                            OutlinedTextField(end, { end = it }, label = { Text(t(language, 18)) }, modifier = Modifier.fillMaxWidth())
                            NumberField(t(language, 15), initial) { initial = it }
                            NumberField(t(language, 16), current) { current = it }
                            NumberField(t(language, 14), inflation) { inflation = it }
                            val a = initial.toDoubleOrNull()
                            val b = current.toDoubleOrNull()
                            val i = inflation.toDoubleOrNull()
                            if (a != null && b != null && i != null && a > 0 && i > -100) {
                                val needed = a * (1 + i / 100)
                                val real = ((b / needed) - 1) * 100
                                Text("Required to maintain purchasing power: %.2f".format(Locale.US, needed))
                                Text("Nominal change: %+.2f%%".format(Locale.US, (b / a - 1) * 100))
                                Text("Real change: %+.2f%%".format(Locale.US, real), color = teal, fontWeight = FontWeight.Bold)
                                Text("Monthly difference against inflation-adjusted initial income: %+.2f".format(Locale.US, b - needed))
                            }
                        }
                        "currency" -> {
                            Text("ECB reference exchange rate against EUR; latest available observation, NOT a historical rate.")
                            OutlinedTextField(currency, { currency = it.uppercase(Locale.ROOT).take(3) }, label = { Text("ISO currency (e.g. USD, GBP, CAD)") }, modifier = Modifier.fillMaxWidth())
                            NumberField("EUR amount", amount) { amount = it }
                            Button(onClick = { request = "/v1/exchange-rates/" + currency }) { Text(t(language, 12)) }
                            Text("Conversion must use the published rate and date in the API response. A historical conversion endpoint is not yet available.")
                        }
                        "compare" -> Button(onClick = {
                            request = "/v1/earnwage/compare?country_a=$country&country_b=$destination&occupation=" + query(occupation)
                        }) { Text(t(language, 12)) }
                        "salary" -> {
                            NumberField(t(language, 13) + " (optional)", annual) { annual = it }
                            Button(onClick = {
                                request = "/v1/earnwage/overview?country=$country&occupation=" + query(occupation) +
                                    (annual.toDoubleOrNull()?.takeIf { it > 0 }?.let { "&annual_gross=$it" } ?: "")
                            }) { Text(t(language, 12)) }
                            Text("Official national occupation data when available; tax components are partial and must not be read as net pay.")
                        }
                        "jobs" -> {
                            Button(onClick = { request = "/v1/jobs?country=$country&occupation=" + query(occupation) }) { Text(t(language, 12)) }
                            Text("Remote jobs only. Country selection means candidate eligibility, not employer location. Source: Remotive.")
                        }
                        "about" -> {
                            Text("EarnWage v0.1.0 · com.earnwage.app")
                            Text("Your salary. Your world.")
                            Text("Explore inflation, purchasing power, exchange rates, official occupational wages and attributed remote vacancies.")
                            Text("Developed by Gil Pereira")
                            Text("API: " + BuildConfig.API_BASE_URL)
                            Text("Sources: Eurostat, ECB, BLS, Canada Job Bank, Remotive and other attributed official data when available.")
                            Text("Missing data are marked unavailable. National wages are not city wages. Inflation is not a city spending basket.")
                            Text(health)
                        }
                    }
                    if (loading) CircularProgressIndicator()
                    if (result.isNotBlank()) {
                        Text(t(language, 19), fontWeight = FontWeight.Bold, color = teal)
                        SelectionContainerSafe(result)
                    }
                }
            }
        }
    }
}
@Composable private fun NumberField(label: String, value: String, change: (String) -> Unit) {
    OutlinedTextField(value, change, label = { Text(label) }, modifier = Modifier.fillMaxWidth(), singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal))
}
@Composable private fun LanguageSelector(value: String, change: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(onClick = { expanded = true }) { Text(languageNames[value] ?: value) }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            languageNames.forEach { (code, name) ->
                DropdownMenuItem(text = { Text(name) }, onClick = { change(code); expanded = false })
            }
        }
    }
}
@Composable private fun CountrySelector(label: String, entries: List<Country>, selected: String, change: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val item = entries.find { it.code == selected }
    Box {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text("$label: " + flag(selected) + " " + (item?.name ?: selected) + " · " + (item?.currency ?: ""), maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            entries.forEach { c ->
                DropdownMenuItem(text = { Text(flag(c.code) + " " + c.name + " · " + c.currency) }, onClick = { change(c.code); expanded = false })
            }
        }
    }
}
@Composable private fun JobSelector(label: String, entries: List<Job>, selected: String, change: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text("$label: " + (entries.find { it.id == selected }?.label ?: selected), maxLines = 1)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            entries.forEach { j ->
                DropdownMenuItem(text = { Text(j.label) }, onClick = { change(j.id); expanded = false })
            }
        }
    }
}
@Composable private fun SelectionContainerSafe(text: String) {
    androidx.compose.foundation.text.selection.SelectionContainer {
        Text(text, fontSize = 12.sp, color = navy, modifier = Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(12.dp)).padding(12.dp))
    }
}
