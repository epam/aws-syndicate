/*
 * Copyright 2024 EPAM Systems, Inc.
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
package com.demoapigatewaycognito.dto;

import org.json.JSONObject;

/**
 * Created by Roman Ivanov on 7/20/2024.
 */
public record SignIn(String nickName, String password) {

    public SignIn {
        if (nickName == null || password == null) {
            throw new IllegalArgumentException("Missing or incomplete data.");
        }
    }

    public static SignIn fromJson(String jsonString) {
        JSONObject json = new JSONObject(jsonString);
        String nickName = json.optString("nickName", null);
        String password = json.optString("password", null);

        return new SignIn(nickName, password);
    }

}
