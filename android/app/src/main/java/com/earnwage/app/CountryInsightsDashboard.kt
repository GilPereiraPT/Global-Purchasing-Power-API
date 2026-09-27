package com.earnwage.app

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.text.NumberFormat
import java.util.Locale

/* The same source-backed observations as docs/country-insights.html and
 * docs/economic-compare.html. These are two different statistical families:
 * World Bank annual WDI and Eurostat/ONS/OECD reference observations.
 * Never infer a country score, national wage from a capital, or personal net pay.
 */
private val ink=Color(0xFF102D38)
private val green=Color(0xFF087F73)
private val amber=Color(0xFFF1D28C)
private val chartColours=listOf(green,Color(0xFFB25C38),Color(0xFF526CC2),
    Color(0xFFA35487),Color(0xFF7B8942))
private data class IndicatorSpec(val key:String,val pt:String,val en:String,
    val unitPt:String,val unitEn:String,val category:Int)
private val metrics=listOf(
    IndicatorSpec("inflation_annual","Inflação anual (IPC)","Annual CPI inflation","%","%",0),
    IndicatorSpec("unemployment","Desemprego","Unemployment","% da população ativa","% of labour force",0),
    IndicatorSpec("gdp_per_capita","PIB per capita","GDP per capita","USD correntes / pessoa","current USD / person",0),
    IndicatorSpec("ppp_private_consumption","PPC do consumo das famílias","Household consumption PPP",
        "moeda local por dólar internacional","local currency / international dollar",0),
    IndicatorSpec("life_expectancy","Esperança de vida","Life expectancy","anos","years",1),
    IndicatorSpec("gini","Índice de Gini","Gini index","índice 0–100","index 0–100",1),
    IndicatorSpec("health_coverage","Cobertura de saúde (UHC)","Health coverage (UHC)",
        "índice 0–100","index 0–100",1),
    IndicatorSpec("primary_completion","Conclusão do ensino primário","Primary completion","%","%",2),
    IndicatorSpec("adult_literacy","Alfabetização de adultos","Adult literacy","%","%",2),
    IndicatorSpec("electricity_access","Acesso a eletricidade","Access to electricity","%","%",3),
    IndicatorSpec("safe_drinking_water","Água potável segura","Safely managed drinking water","%","%",3),
    IndicatorSpec("safe_sanitation","Saneamento seguro","Safely managed sanitation","%","%",3),
    IndicatorSpec("internet_use","Utilização da Internet","Internet use","%","%",3)
)
private val categoriesPt=listOf("Economia e emprego","Saúde e sociedade","Educação","Condições de vida")
private val categoriesEn=listOf("Economy and employment","Health and society","Education","Living conditions")
private val euroCountries=setOf("PT","ES","DE","FR","IE","NL","IT","GB","CH")

private fun label(spec:IndicatorSpec,pt:Boolean)=if(pt)spec.pt else spec.en
private fun unit(spec:IndicatorSpec,pt:Boolean)=if(pt)spec.unitPt else spec.unitEn
private fun dec(value:Double):String =
    NumberFormat.getNumberInstance(Locale.forLanguageTag("pt-PT")).apply {
        maximumFractionDigits=2; minimumFractionDigits=0
    }.format(value)
private fun fmtMoney(value:Double,currency:String):String =
    try {NumberFormat.getCurrencyInstance(Locale.forLanguageTag("pt-PT")).apply {
        this.currency=java.util.Currency.getInstance(currency)
        maximumFractionDigits=2
    }.format(value)} catch (_:Exception) {dec(value)+" "+currency}
private fun flag(code:String):String {
    if(code.length!=2)return code
    val a=code.uppercase(Locale.ROOT)
    return String(Character.toChars(0x1F1E6+a[0].code-65))+
           String(Character.toChars(0x1F1E6+a[1].code-65))
}
private suspend fun getDashboardJson(path:String):JSONObject=withContext(Dispatchers.IO) {
    val url=URL(BuildConfig.API_BASE_URL+path)
    val connection=url.openConnection() as HttpURLConnection
    try {
        connection.connectTimeout=12000;connection.readTimeout=25000
        connection.setRequestProperty("Accept","application/json")
        connection.setRequestProperty("Cache-Control","no-cache")
        val code=connection.responseCode
        if(code !in 200..299)throw IllegalStateException("HTTP "+code)
        val body=connection.inputStream.bufferedReader().use{it.readText()}
        JSONObject(body)
    } finally {connection.disconnect()}
}
private fun e(s:String)=URLEncoder.encode(s,"UTF-8")
private fun valid(o:JSONObject?):Boolean=o!=null && o.optString("status")=="available" &&
    !o.isNull("value") && o.optDouble("value",Double.NaN).isFinite()
@Composable private fun themeCard()=CardDefaults.cardColors(containerColor=Color(0xFFF8FBF9))
private fun localeText(pt:Boolean,ptText:String,enText:String)=if(pt)ptText else enText

@Composable
internal fun CountryInsightsDashboard(
    places:List<Pair<String,String>>, preferred:String, language:String
) {
    val pt=language=="pt"
    val allowed=places.filter{it.first.length==2}
    val allCodes=allowed.map{it.first}.toSet()
    var tab by remember {mutableIntStateOf(0)}
    var single by remember {mutableStateOf("PT")}
    var countries by remember {mutableStateOf(listOf("PT","ES"))}
    var first by remember {mutableStateOf("PT")}
    var second by remember {mutableStateOf("GB")}
    var metricKey by remember {mutableStateOf("unemployment")}
    var fromYear by remember {mutableStateOf("2000")}
    var toYear by remember {mutableStateOf("2026")}
    var singleRequest by remember {mutableIntStateOf(1)}
    var compareRequest by remember {mutableIntStateOf(1)}
    var historyRequest by remember {mutableIntStateOf(1)}
    var economyRequest by remember {mutableIntStateOf(1)}
    var singleData by remember {mutableStateOf<JSONObject?>(null)}
    var compareData by remember {mutableStateOf<JSONObject?>(null)}
    var economyData by remember {mutableStateOf<JSONObject?>(null)}
    var historyData by remember {mutableStateOf<Map<String,List<Pair<Int,Double>>>>(emptyMap())}
    var fxData by remember {mutableStateOf<Map<String,JSONObject>>(emptyMap())}
    var error by remember {mutableStateOf("")}
    var loading by remember {mutableStateOf(false)}
    var historiesLoading by remember {mutableStateOf(false)}
    var historicalError by remember {mutableStateOf("")}
    LaunchedEffect(tab,singleRequest,compareRequest,economyRequest,preferred) {
        error=""; loading=true
        try {
            when(tab) {
                0 -> {singleData=getDashboardJson("/v1/countries/"+single+"/indicators")}
                1 -> {compareData=getDashboardJson("/v1/compare/indicators?countries="+
                    e(countries.joinToString(",")))}
                2 -> {
                    if(first==second)throw IllegalArgumentException(
                        localeText(pt,"Escolhe dois países diferentes.","Choose two different countries."))
                    economyData=getDashboardJson("/v1/eurostat/compare?country_a="+first+"&country_b="+second)
                    val currencies=listOf("EUR","GBP","CHF",preferred).distinct()
                    val fetched=mutableMapOf<String,JSONObject>()
                    fetched["EUR"]=JSONObject().put("units_per_eur",1.0)
                    for(code in currencies.filter{it!="EUR"}) {
                        try { fetched[code]=getDashboardJson("/v1/exchange-rates/"+code) }
                        catch(ex:Exception){if(ex is CancellationException)throw ex}
                    }
                    fxData=fetched
                }
            }
        }catch(ex:Exception){
            if(ex is CancellationException)throw ex
            error=localeText(pt,"Não foi possível atualizar. Tenta novamente.",
                "Could not refresh. Please try again.")
        }finally{loading=false}
    }
    LaunchedEffect(tab,historyRequest) {
        if(tab !in listOf(0,1)) return@LaunchedEffect
        historiesLoading=true;historicalError="";historyData=emptyMap()
        val start=fromYear.toIntOrNull();val end=toYear.toIntOrNull()
        if(start==null || end==null || start !in 1960..2100 || end !in 1960..2100 || start>end){
            historicalError=localeText(pt,"Verifica o intervalo de anos.","Check the year range.")
            historiesLoading=false
            return@LaunchedEffect
        }
        val result=mutableMapOf<String,List<Pair<Int,Double>>>()
        try{
            for(code in (if(tab==0) listOf(single) else countries)) {
                try {
                    val obj=getDashboardJson("/v1/countries/"+code+"/indicators/"+
                        metricKey+"?history=true")
                    val rows=obj.optJSONArray("history")?:JSONArray()
                    result[code]=(0 until rows.length()).mapNotNull {i ->
                        val row=rows.optJSONObject(i)?:return@mapNotNull null
                        val y=row.optInt("year",-1)
                        val v=row.optDouble("value",Double.NaN)
                        if(y in start..end&&v.isFinite())y to v else null
                    }.distinctBy{it.first}.sortedBy{it.first}
                }catch(ex:Exception){
                    if(ex is CancellationException)throw ex
                    result[code]=emptyList()
                }
            }
            historyData=result
        } catch(ex:Exception) {
            if(ex is CancellationException)throw ex
            historicalError=localeText(pt,"Não foi possível carregar a evolução.",
                "Could not load historical data.")
        }finally{historiesLoading=false}
    }
    val placeName={code:String -> allowed.firstOrNull{it.first==code}?.second?:code}
    Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(14.dp)) {
        Text("Country Insights",fontSize=26.sp,fontWeight=FontWeight.Bold)
        Text(localeText(pt,"Economia, salários e qualidade de vida — dados oficiais.",
            "Economy, wages and quality of life — official data."),
            style=MaterialTheme.typography.bodyMedium,
            color=MaterialTheme.colorScheme.onSurface.copy(alpha=.75f))
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(5.dp)) {
            val labels=if(pt) listOf("Um país","Comparar","Economia") else
                listOf("Country","Compare","Economy")
            labels.forEachIndexed{index,text ->
                FilterChip(selected=tab==index,onClick={tab=index},
                    modifier=Modifier.weight(1f),
                    label={Text(text,maxLines=1,fontSize=12.sp)})
            }
        }
        when(tab){
            0 -> {
                DashboardCountryMenu(localeText(pt,"País","Country"),allowed,single) {
                    single=it;singleData=null;historyData=emptyMap();singleRequest++;historyRequest++
                }
                if(loading) LinearProgressIndicator(Modifier.fillMaxWidth())
                if(error.isNotBlank())DashboardRetry(error) {singleRequest++}
                singleData?.let {obj ->
                    val values=obj.optJSONObject("indicators")?:JSONObject()
                    (0..3).forEach{cat ->
                        Text((if(pt)categoriesPt else categoriesEn)[cat],
                            fontSize=19.sp,fontWeight=FontWeight.Bold,
                            color=MaterialTheme.colorScheme.primary)
                        metrics.filter{it.category==cat}.forEach{spec ->
                            IndicatorTile(spec,values.optJSONObject(spec.key),pt)
                        }
                    }
                    IndicatorTile(IndicatorSpec("safety","Segurança percecionada",
                        "Perceived safety","índice 0–100","index 0–100",3),
                        values.optJSONObject("safety"),pt)
                }
                HorizontalDivider()
                Text(localeText(pt,"Evolução histórica","Historical trends"),
                    fontSize=20.sp,fontWeight=FontWeight.Bold)
                DashboardMetricMenu(metrics,metricKey,pt) {
                    metricKey=it;historyRequest++
                }
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(fromYear,{fromYear=it},Modifier.weight(1f),
                        label={Text(localeText(pt,"De","From"))},singleLine=true)
                    OutlinedTextField(toYear,{toYear=it},Modifier.weight(1f),
                        label={Text(localeText(pt,"Até","To"))},singleLine=true)
                }
                Button(onClick={historyRequest++},Modifier.fillMaxWidth()) {
                    Text(localeText(pt,"Atualizar gráfico","Refresh chart"))
                }
                if(historiesLoading)LinearProgressIndicator(Modifier.fillMaxWidth())
                if(historicalError.isNotBlank())Text(historicalError,
                    color=MaterialTheme.colorScheme.error)
                if(!historiesLoading && historyData.isNotEmpty()) {
                    TrendChart(historyData,listOf(single),placeName,pt)
                    val spec=metrics.firstOrNull{it.key==metricKey}
                    historyData[single].orEmpty().takeLast(15).reversed().forEach{(year,value)->
                        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){
                            Text(year.toString(),fontSize=12.sp)
                            Text(dec(value)+" "+(spec?.let{unit(it,pt)}?:""),
                                fontWeight=FontWeight.SemiBold,fontSize=12.sp)
                        }
                    }
                }
            }
            1 -> {
                Text(localeText(pt,"Seleciona entre 2 e 5 países","Select 2 to 5 countries"),
                    fontWeight=FontWeight.SemiBold)
                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement=Arrangement.spacedBy(7.dp)) {
                    allowed.forEach{(code,_) ->
                        FilterChip(selected=code in countries,onClick={
                            countries=if(code in countries) {
                                if(countries.size>2)countries.filterNot{it==code}else countries
                            }else if(countries.size<5)countries+code else countries
                            compareData=null;historyData=emptyMap();compareRequest++;historyRequest++
                        },label={Text(flag(code)+" "+code)})
                    }
                }
                if(loading)LinearProgressIndicator(Modifier.fillMaxWidth())
                if(error.isNotBlank())DashboardRetry(error){compareRequest++}
                compareData?.let {response ->
                    val rows=response.optJSONArray("countries")?:JSONArray()
                    val byCode=(0 until rows.length()).mapNotNull{rows.optJSONObject(it)}
                        .associateBy{it.optString("country")}
                    val categories=listOf(0,1,2,3)
                    categories.forEach{category->
                        Text((if(pt)categoriesPt else categoriesEn)[category],
                            fontSize=18.sp,fontWeight=FontWeight.Bold,color=MaterialTheme.colorScheme.primary)
                        metrics.filter{it.category==category}.forEach{spec ->
                            ComparisonTile(spec,countries,byCode,placeName,pt)
                        }
                    }
                }
                HorizontalDivider()
                Text(localeText(pt,"Evolução histórica","Historical trends"),fontSize=20.sp,
                    fontWeight=FontWeight.Bold)
                Text(localeText(pt,"Compara o mesmo indicador ao longo dos anos.",
                    "Compare the same indicator across years."),
                    style=MaterialTheme.typography.bodySmall)
                DashboardMetricMenu(metrics,metricKey,pt){
                    metricKey=it;historyRequest++
                }
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(fromYear,{fromYear=it},Modifier.weight(1f),
                        label={Text(localeText(pt,"De","From"))},singleLine=true)
                    OutlinedTextField(toYear,{toYear=it},Modifier.weight(1f),
                        label={Text(localeText(pt,"Até","To"))},singleLine=true)
                }
                Button(onClick={historyRequest++},Modifier.fillMaxWidth()) {
                    Text(localeText(pt,"Atualizar gráfico","Refresh chart"))
                }
                if(historiesLoading)LinearProgressIndicator(Modifier.fillMaxWidth())
                if(historicalError.isNotBlank())Text(historicalError,
                    color=MaterialTheme.colorScheme.error)
                if(!historiesLoading && historyData.isNotEmpty()) {
                    TrendChart(historyData,countries,placeName,pt)
                    val chosen=metrics.firstOrNull{it.key==metricKey}
                    val keys=historyData.values.flatMap{it.map{r->r.first}}.distinct().sortedDescending()
                    if(keys.isNotEmpty()) {
                        Text(localeText(pt,"Valores anuais","Annual values"),fontWeight=FontWeight.Bold)
                        keys.take(20).forEach {year ->
                            Card(colors=themeCard(),modifier=Modifier.fillMaxWidth()) {
                                Column(Modifier.padding(12.dp)) {
                                    Text(year.toString(),fontWeight=FontWeight.Bold)
                                    countries.forEach{code->
                                        val v=historyData[code]?.firstOrNull{it.first==year}?.second
                                        Text(flag(code)+" "+placeName(code)+": "+
                                            (if(v!=null)dec(v)+" "+(chosen?.let{unit(it,pt)}?:"")
                                             else "—"),fontSize=12.sp)
                                    }
                                }
                            }
                        }
                        Text(localeText(pt,
                            "— significa ausência de dados nesse ano. As linhas não ligam anos em falta.",
                            "— means no observation for that year. Missing years are not connected."),
                            fontSize=11.sp)
                    }
                }
            }
            else -> {
                Text(localeText(pt,
                    "Compara rendimentos de referência, nível de preços e inflação.",
                    "Compare reference earnings, price levels and inflation."),
                    style=MaterialTheme.typography.bodyMedium)
                val supported=allowed.filter{it.first in euroCountries}
                DashboardCountryMenu(localeText(pt,"País A","Country A"),supported,first){
                    first=it;economyData=null;economyRequest++
                }
                DashboardCountryMenu(localeText(pt,"País B","Country B"),supported,second){
                    second=it;economyData=null;economyRequest++
                }
                Text(localeText(pt,"Moeda de apresentação: ","Display currency: ")+preferred,
                    fontSize=12.sp,color=MaterialTheme.colorScheme.secondary)
                if(loading)LinearProgressIndicator(Modifier.fillMaxWidth())
                if(error.isNotBlank())DashboardRetry(error){economyRequest++}
                economyData?.let {economic ->
                    val rows=economic.optJSONArray("countries")?:JSONArray()
                    val a=rows.optJSONObject(0)?.optJSONObject("indicators")
                    val b=rows.optJSONObject(1)?.optJSONObject("indicators")
                    Text(flag(first)+" "+placeName(first)+"    ·    "+flag(second)+" "+placeName(second),
                        fontSize=15.sp,fontWeight=FontWeight.Bold)
                    EconomicPair("net_annual_earnings_reference",
                        localeText(pt,"Salário líquido anual de referência",
                            "Annual net earnings reference"),a,b,first,second,preferred,
                        fxData,pt,monetary=true)
                    EconomicPair("adjusted",
                        localeText(pt,"Salário ajustado ao nível de preços (indicativo)",
                            "Price-level-adjusted earnings (indicative)"),
                        a,b,first,second,preferred,fxData,pt,monetary=true)
                    EconomicPair("household_price_level_eu27",
                        localeText(pt,"Nível de preços (UE27=100)","Price level (EU27=100)"),
                        a,b,first,second,preferred,fxData,pt)
                    EconomicPair("hicp_annual_change_monthly",
                        localeText(pt,"Inflação homóloga","Year-on-year inflation"),
                        a,b,first,second,preferred,fxData,pt)
                    Text(localeText(pt,
                        "Comparação de referências estatísticas, não de salários pessoais. O IPC britânico e o IHPC europeu têm metodologias distintas.",
                        "Statistical reference comparison, not personal pay. UK CPI and European HICP use distinct methods."),
                        fontSize=11.sp,color=MaterialTheme.colorScheme.onSurface.copy(alpha=.7f))
                }
            }
        }
    }
}
@Composable private fun DashboardRetry(message:String,retry:()->Unit){
    Column(verticalArrangement=Arrangement.spacedBy(6.dp)) {
        Text(message,color=MaterialTheme.colorScheme.error,fontSize=13.sp)
        OutlinedButton(onClick=retry){Text("↻  Tentar novamente / Retry")}
    }
}
@Composable private fun DashboardCountryMenu(
    label:String,places:List<Pair<String,String>>,selected:String,onChange:(String)->Unit
) {
    var open by remember{mutableStateOf(false)}
    Box(Modifier.fillMaxWidth()){
        OutlinedButton(onClick={open=true},modifier=Modifier.fillMaxWidth()) {
            Text(label+": "+flag(selected)+" "+
                (places.firstOrNull{it.first==selected}?.second?:selected),
                maxLines=1,overflow=TextOverflow.Ellipsis,modifier=Modifier.weight(1f))
            Text(" ▾")
        }
        DropdownMenu(expanded=open,onDismissRequest={open=false}) {
            places.forEach{(code,name)->
                DropdownMenuItem(text={Text(flag(code)+" "+name)},
                    onClick={open=false;onChange(code)})
            }
        }
    }
}
@Composable private fun DashboardMetricMenu(
    options:List<IndicatorSpec>,selected:String,pt:Boolean,onChange:(String)->Unit
) {
    var open by remember{mutableStateOf(false)}
    val current=options.firstOrNull{it.key==selected}
    Box {
        OutlinedButton(onClick={open=true},modifier=Modifier.fillMaxWidth()) {
            Text(localeText(pt,"Indicador: ","Indicator: ")+
                (current?.let{label(it,pt)}?:selected),modifier=Modifier.weight(1f))
            Text(" ▾")
        }
        DropdownMenu(expanded=open,onDismissRequest={open=false}) {
            options.forEach{opt->
                DropdownMenuItem(text={Text(label(opt,pt))},onClick={open=false;onChange(opt.key)})
            }
        }
    }
}
@Composable private fun IndicatorTile(spec:IndicatorSpec,datum:JSONObject?,pt:Boolean) {
    val uri=LocalUriHandler.current
    var details by remember(spec.key){mutableStateOf(false)}
    val available=valid(datum)
    val value=if(available)dec(datum!!.optDouble("value"))+" "+unit(spec,pt) else
        localeText(pt,"Sem dados","No data")
    Card(colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface),
        modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(16.dp)){
        Column(Modifier.padding(15.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
            Text(label(spec,pt),fontSize=13.sp,color=MaterialTheme.colorScheme.secondary,
                fontWeight=FontWeight.SemiBold)
            Text(value,fontSize=22.sp,fontWeight=FontWeight.Bold)
            if(available) {
                Text(localeText(pt,"Ano: ","Year: ")+datum!!.optString("year"),
                    fontSize=12.sp,color=MaterialTheme.colorScheme.onSurface.copy(alpha=.65f))
            }else if(datum?.optString("status")=="not_imported") {
                Text(localeText(pt,"A aguardar dados oficiais","Awaiting official data"),
                    fontSize=12.sp)
            }
            TextButton(onClick={details=!details},contentPadding=PaddingValues(0.dp)) {
                Text(localeText(pt,"Fonte e detalhes","Source and details")+"  "+
                    if(details)"▴" else "▾",fontSize=12.sp)
            }
            if(details){
                Text(datum?.optString("source")?.takeIf{it!="null"}?:
                    localeText(pt,"Fonte indisponível","Source unavailable"),fontSize=12.sp)
                val source=datum?.optString("source_url").orEmpty()
                if(source.startsWith("https://"))TextButton(onClick={uri.openUri(source)}) {
                    Text(localeText(pt,"Consultar fonte ↗","View source ↗"),fontSize=12.sp)
                }
                val refresh=datum?.optString("last_successful_refresh").orEmpty()
                if(refresh.isNotBlank()&&refresh!="null")Text(
                    localeText(pt,"Base atualizada: ","Database updated: ")+refresh.take(10),
                    fontSize=11.sp)
            }
        }
    }
}
@Composable private fun ComparisonTile(
    spec:IndicatorSpec,codes:List<String>,rows:Map<String,JSONObject>,
    countryName:(String)->String,pt:Boolean
){
    Card(colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface),
        modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(16.dp)){
        Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(9.dp)) {
            Text(label(spec,pt),fontSize=13.sp,color=MaterialTheme.colorScheme.secondary,
                fontWeight=FontWeight.SemiBold)
            codes.forEach{code->
                val datum=rows[code]?.optJSONObject("indicators")?.optJSONObject(spec.key)
                Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){
                    Text(flag(code)+" "+countryName(code),fontSize=12.sp,modifier=Modifier.weight(1f))
                    Column(horizontalAlignment=Alignment.End) {
                        Text(if(valid(datum))dec(datum!!.optDouble("value"))+" "+unit(spec,pt)
                            else "—",fontWeight=FontWeight.SemiBold,fontSize=13.sp)
                        if(valid(datum))Text(datum!!.optString("year"),fontSize=10.sp,
                            color=MaterialTheme.colorScheme.onSurface.copy(alpha=.6f))
                    }
                }
            }
        }
    }
}
@Composable private fun TrendChart(
    history:Map<String,List<Pair<Int,Double>>>,codes:List<String>,
    names:(String)->String,pt:Boolean
){
    val total=history.values.flatten()
    if(total.isEmpty()){
        Text(localeText(pt,"Sem observações para o intervalo selecionado.",
            "No observations for the selected years."),fontSize=13.sp)
        return
    }
    val minYear=total.minOf{it.first}
    val maxYear=total.maxOf{it.first}
    val minValue=total.minOf{it.second}
    val maxValue=total.maxOf{it.second}
    val spread=(maxValue-minValue).takeIf{it>0}?:maxOf(kotlin.math.abs(maxValue)*.05,1.0)
    val lo=minValue-spread*.12;val hi=maxValue+spread*.12
    Card(colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface),
        shape=RoundedCornerShape(18.dp)) {
        Column(Modifier.fillMaxWidth().padding(14.dp),
            verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Text(dec(hi),fontSize=10.sp)
            Canvas(Modifier.fillMaxWidth().height(205.dp)) {
                val w=size.width;val h=size.height
                repeat(5){idx->
                    val y=h*idx/4f
                    drawLine(Color.Gray.copy(alpha=.22f),Offset(0f,y),Offset(w,y),1.dp.toPx())
                }
                val xFor={yr:Int -> (yr-minYear).toFloat()/
                    (maxYear-minYear).coerceAtLeast(1).toFloat()*w}
                val yFor={v:Double -> ((hi-v)/(hi-lo)).toFloat()*h}
                codes.forEachIndexed {idx,code->
                    val values=history[code].orEmpty()
                    values.zipWithNext().forEach{(a,b)->
                        if(b.first==a.first+1)drawLine(chartColours[idx%chartColours.size],
                            Offset(xFor(a.first),yFor(a.second)),
                            Offset(xFor(b.first),yFor(b.second)),2.4.dp.toPx())
                    }
                    values.forEach{(year,value)->
                        drawCircle(chartColours[idx%chartColours.size],3.dp.toPx(),
                            Offset(xFor(year),yFor(value)))
                    }
                }
            }
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){
                Text(minYear.toString(),fontSize=11.sp)
                Text(maxYear.toString(),fontSize=11.sp)
            }
            Text(dec(lo),fontSize=10.sp)
            codes.forEachIndexed{idx,code->
                Row(verticalAlignment=Alignment.CenterVertically,
                    horizontalArrangement=Arrangement.spacedBy(7.dp)){
                    Surface(color=chartColours[idx%chartColours.size],
                        shape=RoundedCornerShape(3.dp),modifier=Modifier.size(18.dp,5.dp)){}
                    Text(flag(code)+" "+names(code),fontSize=12.sp)
                }
            }
        }
    }
}
private fun originalCurrency(item:JSONObject?)=when(item?.optString("unit")){
    "EUR_per_year"->"EUR";"GBP_per_year"->"GBP";else->null
}
private fun convertible(n:Double,from:String,to:String,
    rates:Map<String,JSONObject>):Double?{
    if(from==to)return n
    val a=if(from=="EUR")1.0 else rates[from]?.optDouble("units_per_eur",Double.NaN)
    val b=if(to=="EUR")1.0 else rates[to]?.optDouble("units_per_eur",Double.NaN)
    if(a==null||b==null||!a.isFinite()||!b.isFinite()||a<=0||b<=0)return null
    val dA=rates[from]?.optString("period").orEmpty()
    val dB=rates[to]?.optString("period").orEmpty()
    if(dA.isNotBlank()&&dB.isNotBlank()&&dA!=dB)return null
    return n*b/a
}
@Composable private fun EconomicPair(
    key:String,title:String,a:JSONObject?,b:JSONObject?,
    aCode:String,bCode:String,preferred:String,rates:Map<String,JSONObject>,
    pt:Boolean,monetary:Boolean=false
){
    Card(colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface),
        shape=RoundedCornerShape(18.dp)){
        Column(Modifier.fillMaxWidth().padding(14.dp),
            verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Text(title,fontWeight=FontWeight.Bold,fontSize=14.sp,
                color=MaterialTheme.colorScheme.secondary)
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(9.dp)) {
                listOf(aCode to a,bCode to b).forEach{(code,indicators)->
                    val wage=indicators?.optJSONObject("net_annual_earnings_reference")
                    val prices=indicators?.optJSONObject("household_price_level_eu27")
                    val item=if(key=="adjusted")wage else indicators?.optJSONObject(key)
                    val validValue=valid(item)
                    var value:String=localeText(pt,"Sem dados","No data")
                    var caption=""
                    if(validValue){
                        val v=item!!.optDouble("value")
                        val sourceCurrency=originalCurrency(item)
                        if(key=="adjusted"){
                            val p=prices?.optDouble("value",Double.NaN)?:Double.NaN
                            val converted=sourceCurrency?.let {
                                convertible(v,it,preferred,rates)
                            }
                            if(valid(prices)&&p>0&&converted!=null)
                                value=fmtMoney(converted/(p/100),preferred)
                            caption=item.optString("period")+" · "+
                                (prices?.optString("period")?:"")
                        }else if(monetary&&sourceCurrency!=null){
                            val converted=convertible(v,sourceCurrency,preferred,rates)
                            if(converted!=null)value=fmtMoney(converted,preferred)
                            caption=localeText(pt,"Original: ","Original: ")+
                                fmtMoney(v,sourceCurrency)+" · "+item.optString("period")
                        }else{
                            value=dec(v)+(if(key=="hicp_annual_change_monthly")"%" else "")
                            caption=item.optString("period")+
                                (if(key=="household_price_level_eu27")" · UE27=100"
                                else if(code=="GB")" · CPI" else " · IHPC/HICP")
                        }
                    }
                    Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(6.dp)){
                        Text(flag(code)+" "+code,fontSize=12.sp)
                        Text(value,fontSize=18.sp,fontWeight=FontWeight.Bold,
                            color=MaterialTheme.colorScheme.onSurface)
                        Text(caption,fontSize=10.sp,
                            color=MaterialTheme.colorScheme.onSurface.copy(alpha=.7f))
                        val source=item?.optString("source_url").orEmpty()
                        val uri=LocalUriHandler.current
                        if(source.startsWith("https://"))TextButton(
                            onClick={uri.openUri(source)},
                            contentPadding=PaddingValues(0.dp)
                        ){Text(localeText(pt,"Fonte ↗","Source ↗"),fontSize=11.sp)}
                    }
                }
            }
        }
    }
}
