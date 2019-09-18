package org.gluu.casa.timer;

import java.util.Set;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;

@JsonIgnoreProperties(ignoreUnknown = true)
public class PluginMetric {

    private String pluginId;
    private String version;
    private int daysUsed;

    @JsonInclude(JsonInclude.Include.NON_EMPTY)
    private Set<String> activeUsers;

    public String getPluginId() {
        return pluginId;
    }

    public void setPluginId(String pluginId) {
        this.pluginId = pluginId;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public int getDaysUsed() {
        return daysUsed;
    }

    public void setDaysUsed(int daysUsed) {
        this.daysUsed = daysUsed;
    }

    public Set<String> getActiveUsers() {
        return activeUsers;
    }

    public void setActiveUsers(Set<String> activeUsers) {
        this.activeUsers = activeUsers;
    }

}
