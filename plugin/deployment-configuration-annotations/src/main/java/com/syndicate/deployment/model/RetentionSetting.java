/*
 * Copyright 2018 EPAM Systems, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.syndicate.deployment.model;

/**
 * Created by Roman Ivanov on 1/29/2024.
 */
public enum RetentionSetting {

    SYNDICATE_DEFAULT_SPECIFIED(null),
    SYNDICATE_ALIASES_SPECIFIED("${logs_expiration}"),
    ONE_DAY("1"),
    THREE_DAYS("3"),
    FIVE_DAYS("5"),
    ONE_WEEK("7"),
    TWO_WEEKS("14"),
    ONE_MONTH("30"),
    TWO_MONTHS("60"),
    THREE_MONTHS("90"),
    FOUR_MONTHS("120"),
    FIVE_MONTHS("150"),
    SIX_MONTHS("180"),
    TWELVE_MONTHS("365"),
    THIRTEEN_MONTHS("400"),
    EIGHTEEN_MONTHS("545"),
    TWO_YEARS("731"),
    THREE_YEARS("1096"),
    FIVE_YEARS("1827"),
    SIX_YEARS("2192"),
    SEVEN_YEARS("2557"),
    EIGHT_YEARS("2922"),
    NINE_YEARS("3288"),
    TEN_YEARS("3653");

    private final String days;

    RetentionSetting(String days) {
        this.days = days;
    }

    public String getValue() {
        return days;
    }
}
